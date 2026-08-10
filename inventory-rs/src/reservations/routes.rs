use super::errors::ReservationError;
use super::schemas::{ReserveRequest, ReserveResponse};
use super::service::ReservationService;
use crate::AppState;
use axum::{Json, Router, extract::State, routing::post};

pub async fn reserve_inventory(
    State(state): State<AppState>,
    Json(payload): Json<ReserveRequest>,
) -> Result<Json<ReserveResponse>, ReservationError> {
    let service = ReservationService {
        db_pool: state.db_pool,
        http_client: state.http_client,
        shipping_url: state.shipping_url,
    };

    let response = service.reserve(payload).await?;

    Ok(Json(response))
}

pub fn router() -> Router<AppState> {
    Router::new().route("/reserve", post(reserve_inventory))
}
