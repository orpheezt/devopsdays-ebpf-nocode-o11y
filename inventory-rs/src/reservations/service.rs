use super::models::Reservation;
use super::schemas::{ReserveRequest, ReserveResponse, ShippingInfo};
use tracing::{error, info};
use uuid::Uuid;

pub struct ReservationService {
    pub db_pool: toasty::Db,
    pub http_client: reqwest::Client,
    pub shipping_url: String,
}

impl ReservationService {
    pub async fn reserve(&self, payload: ReserveRequest) -> Result<ReserveResponse, String> {
        let reservation_id = Uuid::now_v7().to_string();

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
                format!("Failed to reach shipping service: {}", err)
            })?;

        if !resp.status().is_success() {
            let status = resp.status();
            error!("Shipping service returned status {}", status);
            return Err(format!("Shipping service returned status {}", status));
        }

        let shipping_info = resp.json::<ShippingInfo>().await.map_err(|err| {
            error!("Failed to parse shipping quote: {}", err);
            format!("Failed to parse shipping quote: {}", err)
        })?;

        let reservation = Reservation {
            reservation_id: reservation_id.clone(),
            order_id: payload.order_id.clone(),
            items_count: payload.items_count,
            status: "RESERVED".to_string(),
        };

        let mut db = self.db_pool.clone();
        toasty::create!(Reservation {
            reservation_id: reservation.reservation_id.clone(),
            order_id: reservation.order_id.clone(),
            items_count: reservation.items_count,
            status: reservation.status.clone(),
        })
        .exec(&mut db)
        .await
        .map_err(|e| {
            error!("Failed to create reservation record with Toasty: {}", e);
            "Database error".to_string()
        })?;

        info!(
            "Successfully reserved inventory {} for order {}",
            reservation_id, payload.order_id
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

