#[derive(Debug, toasty::Model)]
pub struct Reservation {
    #[key]
    pub reservation_id: String,
    pub order_id: String,
    pub items_count: i32,
    pub status: String,
}
