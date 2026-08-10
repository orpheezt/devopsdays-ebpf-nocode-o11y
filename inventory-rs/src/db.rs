use thiserror::Error;

pub struct DbConfig {
    pub url: String,
}

pub async fn get_db_pool(config: DbConfig) -> Result<toasty::Db, DbError> {
    let max_retries = 5;
    let mut attempt = 0;

    loop {
        attempt += 1;
        match toasty::Db::builder()
            .models(toasty::models![crate::inventory::Inventory, crate::reservations::models::Reservation])
            .connect(&config.url)
            .await
        {
            Ok(db) => return Ok(db),
            Err(e) => {
                if attempt >= max_retries {
                    return Err(DbError::ConnectionFailed(format!(
                        "Failed after {} attempts: {}",
                        max_retries, e
                    )));
                }
                tracing::warn!(
                    "Database connection attempt {}/{} failed: {}. Retrying in 1 second...",
                    attempt,
                    max_retries,
                    e
                );
                tokio::time::sleep(std::time::Duration::from_secs(1)).await;
            }
        }
    }
}

#[derive(Error, Debug)]
pub enum DbError {
    #[error("Database connection failed: {0}")]
    ConnectionFailed(String),
}
