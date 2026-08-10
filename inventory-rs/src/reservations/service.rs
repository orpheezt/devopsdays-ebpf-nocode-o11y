use super::errors::ReservationError;
use super::models::Reservation;
use super::schemas::{ReserveRequest, ReserveResponse, ShippingInfo};
use crate::inventory::Inventory;
use tracing::{error, info};
use uuid::Uuid;

pub struct ReservationService {
    pub db_pool: toasty::Db,
    pub http_client: reqwest::Client,
    pub shipping_url: String,
}

impl ReservationService {
    pub async fn reserve(
        &self,
        payload: ReserveRequest,
    ) -> Result<ReserveResponse, ReservationError> {
        let items = payload.normalized_items();
        if items.is_empty() {
            return Err(ReservationError::InvalidInput(
                "items_count must be greater than 0".to_string(),
            ));
        }

        for item in &items {
            if item.quantity <= 0 {
                return Err(ReservationError::InvalidInput(
                    "items_count must be greater than 0".to_string(),
                ));
            }
        }

        let mut db = self.db_pool.clone();
        let mut updates = Vec::new();

        for item in &items {
            let inv_item = match Inventory::get_by_product_id(&mut db, &item.product_id).await {
                Ok(inv) => inv,
                Err(e) => {
                    error!("Failed to fetch inventory item {}: {}", item.product_id, e);
                    return Err(ReservationError::ProductNotFound(item.product_id));
                }
            };

            if inv_item.stock_quantity < item.quantity {
                return Err(ReservationError::InsufficientStock {
                    product_id: item.product_id,
                    requested: item.quantity,
                    available: inv_item.stock_quantity,
                });
            }

            updates.push((inv_item, item.quantity));
        }

        let reservation_id = Uuid::now_v7();

        let resp = self
            .http_client
            .get(&self.shipping_url)
            .send()
            .await
            .map_err(|err| {
                error!(
                    "Failed to reach shipping service ({}): {}",
                    self.shipping_url, err
                );
                ReservationError::ShippingServiceUnavailable(err.to_string())
            })?;

        if !resp.status().is_success() {
            let status = resp.status();
            error!("Shipping service returned status {}", status);
            return Err(ReservationError::ShippingServiceUnavailable(format!(
                "Status {}",
                status
            )));
        }

        let shipping_info = resp.json::<ShippingInfo>().await.map_err(|err| {
            error!("Failed to parse shipping quote: {}", err);
            ReservationError::ShippingServiceUnavailable(format!("Failed to parse quote: {}", err))
        })?;

        let mut total_reserved: i32 = 0;
        for (mut inv_item, qty) in updates {
            let new_reserved = inv_item.reserved_quantity + qty;
            let new_stock = inv_item.stock_quantity - qty;

            inv_item
                .update()
                .reserved_quantity(new_reserved)
                .stock_quantity(new_stock)
                .exec(&mut db)
                .await
                .map_err(|e| {
                    error!("Failed to update inventory stock: {}", e);
                    ReservationError::DatabaseError("Failed to update inventory stock".to_string())
                })?;

            total_reserved += qty;
        }

        let reservation = Reservation {
            reservation_id,
            order_id: payload.order_id,
            items_count: total_reserved,
            status: "RESERVED".to_string(),
        };

        toasty::create!(Reservation {
            reservation_id: reservation.reservation_id,
            order_id: reservation.order_id,
            items_count: reservation.items_count,
            status: reservation.status.clone(),
        })
        .exec(&mut db)
        .await
        .map_err(|e| {
            error!("Failed to create reservation record with Toasty: {}", e);
            ReservationError::DatabaseError("Failed to save reservation".to_string())
        })?;

        info!(
            "Successfully reserved {} total items across {} product(s) for order {}",
            total_reserved,
            items.len(),
            payload.order_id
        );

        Ok(ReserveResponse {
            reservation_id,
            order_id: payload.order_id,
            items_reserved: total_reserved,
            status: "RESERVED".into(),
            shipping_info,
        })
    }
}
