use super::schemas::{HealthStatusResponse, ReadinessStatusResponse};
use crate::AppState;
use axum::{Json, Router, extract::State, http::StatusCode, response::IntoResponse, routing::get};

pub async fn liveness_check() -> impl IntoResponse {
    Json(HealthStatusResponse::default())
}

async fn check_db(mut db: toasty::Db) -> Result<(), String> {
    toasty::sql::query("SELECT 1")
        .exec(&mut db)
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn readiness_check(State(state): State<AppState>) -> impl IntoResponse {
    match check_db(state.db_pool.clone()).await {
        Ok(_) => (StatusCode::OK, Json(ReadinessStatusResponse::ok())),
        Err(err) => (
            StatusCode::SERVICE_UNAVAILABLE,
            Json(ReadinessStatusResponse::error(err)),
        ),
    }
}

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/livez", get(liveness_check))
        .route("/readyz", get(readiness_check))
}
