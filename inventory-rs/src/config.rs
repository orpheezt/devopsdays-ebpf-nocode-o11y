pub struct Settings {
    pub db_url: String,
    pub server_addr: String,
    pub shipping_url: String,
}

impl Settings {
    pub fn load() -> Self {
        dotenvy::dotenv().ok();
        Self {
            db_url: std::env::var("DATABASE_URL").unwrap_or_else(|_| {
                "postgres://postgres:postgres@localhost:5432/inventory_db".to_string()
            }),
            server_addr: std::env::var("SERVER_ADDR")
                .unwrap_or_else(|_| "0.0.0.0:8082".to_string()),
            shipping_url: std::env::var("SHIPPING_SERVICE_URL")
                .unwrap_or_else(|_| "http://shipping-quarkus:8084/quote".to_string()),
        }
    }
}
