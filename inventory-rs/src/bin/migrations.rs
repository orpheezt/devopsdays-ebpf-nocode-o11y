use toasty_cli::{Config, ToastyCli};
use tracing::{error, info};

#[tokio::main]
async fn main() {
    dotenvy::dotenv().ok();
    tracing_subscriber::fmt::init();

    let config = match Config::load() {
        Ok(config) => config,
        Err(err) => {
            error!(%err, "Failed to load toasty configuration.");
            std::process::exit(1);
        }
    };

    let settings = inventory_rs::Settings::load();

    let db = match inventory_rs::db::get_db_pool(inventory_rs::db::DbConfig {
        url: settings.db_url,
    })
    .await
    {
        Ok(db) => db,
        Err(err) => {
            error!(%err, "Failed to connect to database for migrations.");
            std::process::exit(1);
        }
    };
    info!("Successfully connected to DB for migrations.");

    let cli = ToastyCli::with_config(db, config);
    if let Err(err) = cli.parse_and_run().await {
        error!(%err, "Failed to execute migration CLI command.");
        std::process::exit(1);
    }
}
