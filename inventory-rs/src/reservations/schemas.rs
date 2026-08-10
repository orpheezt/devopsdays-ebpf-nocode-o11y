use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Deserialize, Serialize, Clone, PartialEq, Eq)]
pub struct ReserveItem {
    pub product_id: Uuid,
    pub quantity: i32,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct ReserveRequest {
    pub order_id: Uuid,
    #[serde(default)]
    pub product_id: Option<Uuid>,
    #[serde(default)]
    pub items_count: Option<i32>,
    #[serde(default)]
    pub items: Vec<ReserveItem>,
}

impl ReserveRequest {
    pub fn normalized_items(&self) -> Vec<ReserveItem> {
        if !self.items.is_empty() {
            self.items.clone()
        } else if let (Some(product_id), Some(items_count)) = (self.product_id, self.items_count) {
            vec![ReserveItem {
                product_id,
                quantity: items_count,
            }]
        } else {
            Vec::new()
        }
    }
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
