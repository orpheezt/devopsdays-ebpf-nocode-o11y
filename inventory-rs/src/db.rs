use thiserror::Error;

pub struct DbConfig {
    pub url: String,
}

pub async fn get_db_pool(config: DbConfig) -> Result<toasty::Db, DbError> {
    let db = toasty::Db::builder()
        .connect(&config.url)
        .await
        .map_err(|e| DbError::ConnectionFailed(e.to_string()))?;

    Ok(db)
}

#[derive(Error, Debug)]
pub enum DbError {
    #[error("Database connection failed: {0}")]
    ConnectionFailed(String),
}
