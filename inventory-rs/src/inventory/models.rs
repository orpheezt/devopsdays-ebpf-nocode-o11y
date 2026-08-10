#[derive(Debug, toasty::Model)]
pub struct Inventory {
    #[key]
    pub product_id: String,
    pub product_name: String,
    pub stock_quantity: i32,
    pub reserved_quantity: i32,
}
