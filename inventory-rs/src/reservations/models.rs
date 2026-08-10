use uuid::Uuid;

#[derive(Debug, toasty::Model)]
pub struct Reservation {
    #[key]
    pub reservation_id: Uuid,
    pub order_id: Uuid,
    pub items_count: i32,
    pub status: String,
}
