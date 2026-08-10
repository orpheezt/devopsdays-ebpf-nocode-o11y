pub mod config;
pub mod db;
pub mod health;
pub mod inventory;
pub mod reservations;

pub use config::Settings;

use axum::Router;

#[derive(Clone)]
pub struct AppState {
    pub db_pool: toasty::Db,
    pub http_client: reqwest::Client,
    pub shipping_url: String,
}

pub fn root_router(db_pool: toasty::Db, settings: &Settings) -> Router {
    let state = AppState {
        db_pool,
        http_client: reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(5))
            .build()
            .unwrap_or_default(),
        shipping_url: settings.shipping_url.clone(),
    };

    Router::new()
        .merge(health::routes::router())
        .merge(reservations::routes::router())
        .with_state(state)
}
