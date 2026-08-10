use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
pub struct ReserveRequest {
    pub order_id: String,
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
    pub reservation_id: String,
    pub order_id: String,
    pub items_reserved: i32,
    pub status: String,
    pub shipping_info: ShippingInfo,
}
