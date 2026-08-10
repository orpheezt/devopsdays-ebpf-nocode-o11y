use inventory_rs::{Settings, db::DbConfig, db::get_db_pool, root_router};
use tracing::{error, info};

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let settings = Settings::load();

    let db_pool = match get_db_pool(DbConfig {
        url: settings.db_url.clone(),
    })
    .await
    {
        Ok(pool) => pool,
        Err(err) => {
            error!(%err);
            std::process::exit(1);
        }
    };
    info!("Successfully connected to DB.");

    let app = root_router(db_pool, &settings);

    let listener = match tokio::net::TcpListener::bind(&settings.server_addr).await {
        Ok(listener) => listener,
        Err(err) => {
            error!(%err, "Failed to bind to port {}.", settings.server_addr);
            std::process::exit(1);
        }
    };
    info!("Server successfully bound to {}", settings.server_addr);

    info!("Starting Axum web server...");
    if let Err(err) = axum::serve(listener, app).await {
        error!(%err, "Server crashed during runtime.");
        std::process::exit(1);
    }
}
