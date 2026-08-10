use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Deserialize)]
pub struct ReserveRequest {
    pub order_id: Uuid,
    pub product_id: Uuid,
    pub items_count: i32,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ShippingInfo {
    pub carrier: String,
    pub cost: f64,
    pub est_days: i32,
}

#[derive(Debug, Serialize)]
pub struct ReserveResponse {
    pub reservation_id: Uuid,
    pub order_id: Uuid,
    pub items_reserved: i32,
    pub status: String,
    pub shipping_info: ShippingInfo,
}
