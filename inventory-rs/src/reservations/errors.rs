use axum::{
    Json,
    http::StatusCode,
    response::{IntoResponse, Response},
};
use serde::Serialize;
use thiserror::Error;
use uuid::Uuid;

#[derive(Debug, Error)]
pub enum ReservationError {
    #[error("Invalid request input: {0}")]
    InvalidInput(String),

    #[error("Product '{0}' not found")]
    ProductNotFound(Uuid),

    #[error(
        "Insufficient stock for product '{product_id}': requested {requested}, available {available}"
    )]
    InsufficientStock {
        product_id: Uuid,
        requested: i32,
        available: i32,
    },

    #[error("Shipping service error: {0}")]
    ShippingServiceUnavailable(String),

    #[error("Database error: {0}")]
    DatabaseError(String),
}

#[derive(Serialize)]
struct ErrorResponse {
    error: String,
    code: &'static str,
}

impl IntoResponse for ReservationError {
    fn into_response(self) -> Response {
        let (status, code) = match &self {
            ReservationError::InvalidInput(_) => (StatusCode::BAD_REQUEST, "INVALID_INPUT"),
            ReservationError::ProductNotFound(_) => (StatusCode::NOT_FOUND, "PRODUCT_NOT_FOUND"),
            ReservationError::InsufficientStock { .. } => {
                (StatusCode::CONFLICT, "INSUFFICIENT_STOCK")
            }
            ReservationError::ShippingServiceUnavailable(_) => {
                (StatusCode::BAD_GATEWAY, "SHIPPING_SERVICE_UNAVAILABLE")
            }
            ReservationError::DatabaseError(_) => {
                (StatusCode::INTERNAL_SERVER_ERROR, "DATABASE_ERROR")
            }
        };

        let body = Json(ErrorResponse {
            error: self.to_string(),
            code,
        });

        (status, body).into_response()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_status_codes() {
        let err_invalid = ReservationError::InvalidInput("bad count".into());
        assert_eq!(
            err_invalid.into_response().status(),
            StatusCode::BAD_REQUEST
        );

        let dummy_id = Uuid::nil();
        let err_not_found = ReservationError::ProductNotFound(dummy_id);
        assert_eq!(
            err_not_found.into_response().status(),
            StatusCode::NOT_FOUND
        );

        let err_stock = ReservationError::InsufficientStock {
            product_id: dummy_id,
            requested: 10,
            available: 2,
        };
        assert_eq!(err_stock.into_response().status(), StatusCode::CONFLICT);

        let err_shipping = ReservationError::ShippingServiceUnavailable("timeout".into());
        assert_eq!(
            err_shipping.into_response().status(),
            StatusCode::BAD_GATEWAY
        );

        let err_db = ReservationError::DatabaseError("connection lost".into());
        assert_eq!(
            err_db.into_response().status(),
            StatusCode::INTERNAL_SERVER_ERROR
        );
    }
}
