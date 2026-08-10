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
    pub async fn reserve(&self, payload: ReserveRequest) -> Result<ReserveResponse, ReservationError> {
        if payload.items_count <= 0 {
            return Err(ReservationError::InvalidInput(
                "items_count must be greater than 0".to_string(),
            ));
        }

        let product_id = payload.product_id.clone();

        let mut db = self.db_pool.clone();

        let mut item = match Inventory::get_by_product_id(&mut db, &product_id).await {
            Ok(item) => item,
            Err(e) => {
                error!("Failed to fetch inventory item {}: {}", product_id, e);
                return Err(ReservationError::ProductNotFound(product_id));
            }
        };

        if item.stock_quantity < payload.items_count {
            return Err(ReservationError::InsufficientStock {
                product_id: product_id.clone(),
                requested: payload.items_count,
                available: item.stock_quantity,
            });
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
            ReservationError::ShippingServiceUnavailable(format!(
                "Failed to parse quote: {}",
                err
            ))
        })?;

        let new_reserved = item.reserved_quantity + payload.items_count;
        let new_stock = item.stock_quantity - payload.items_count;

        item.update()
            .reserved_quantity(new_reserved)
            .stock_quantity(new_stock)
            .exec(&mut db)
            .await
            .map_err(|e| {
                error!("Failed to update inventory stock: {}", e);
                ReservationError::DatabaseError("Failed to update inventory stock".to_string())
            })?;

        let reservation = Reservation {
            reservation_id,
            order_id: payload.order_id,
            items_count: payload.items_count,
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
            "Successfully reserved {} items of product {} for order {}",
            payload.items_count, product_id, payload.order_id
        );

        Ok(ReserveResponse {
            reservation_id,
            order_id: payload.order_id,
            items_reserved: payload.items_count,
            status: "RESERVED".into(),
            shipping_info,
        })
    }
}

