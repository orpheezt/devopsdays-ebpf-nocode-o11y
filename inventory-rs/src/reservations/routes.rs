use super::schemas::ReserveRequest;
use super::service::ReservationService;
use crate::AppState;
use axum::{Json, Router, extract::State, http::StatusCode, response::IntoResponse, routing::post};

pub async fn reserve_inventory(
    State(state): State<AppState>,
    Json(payload): Json<ReserveRequest>,
) -> Result<impl IntoResponse, (StatusCode, String)> {
    let service = ReservationService {
        db_pool: state.db_pool,
        http_client: state.http_client,
        shipping_url: state.shipping_url,
    };

    let response = service
        .reserve(payload)
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e))?;

    Ok((StatusCode::OK, Json(response)))
}

pub fn router() -> Router<AppState> {
    Router::new().route("/reserve", post(reserve_inventory))
}
