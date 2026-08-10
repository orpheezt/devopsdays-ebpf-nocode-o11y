mod common;

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use inventory_rs::Settings;
use tower::ServiceExt;

#[tokio::test]
async fn test_health_check_endpoint() {
    let (_container, db_url, db_pool) = common::setup_test_db().await;

    let settings = Settings {
        db_url,
        server_addr: "0.0.0.0:8082".into(),
        shipping_url: "http://shipping-quarkus:8084/quote".into(),
    };

    let app = inventory_rs::root_router(db_pool, &settings);

    // Test /livez (liveness probe)
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .uri("/livez")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let body = response.into_body().collect().await.unwrap().to_bytes();
    let body_json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(body_json["status"], "ok");

    // Test /readyz (readiness probe)
    let response = app
        .oneshot(
            Request::builder()
                .uri("/readyz")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let body = response.into_body().collect().await.unwrap().to_bytes();
    let body_json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(body_json["status"], "ok");
    assert_eq!(body_json["database"], "connected");
}

#[tokio::test]
async fn test_reserve_endpoint_integration() {
    let (_container, db_url, db_pool) = common::setup_test_db().await;

    let mut db = db_pool.clone();
    let product_id = uuid::Uuid::parse_str("0191234a-5b6c-7123-9000-000000000000").unwrap();

    toasty::create!(inventory_rs::inventory::Inventory {
        product_id,
        product_name: "Default Product".to_string(),
        stock_quantity: 100,
        reserved_quantity: 0,
    })
    .exec(&mut db)
    .await
    .expect("Failed to seed initial product");

    let mock_shipping_app = axum::Router::new().route(
        "/quote",
        axum::routing::get(|| async {
            axum::Json(serde_json::json!({
                "carrier": "DHL / Servientrega",
                "cost": 12.50,
                "est_days": 2
            }))
        }),
    );
    let mock_listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let mock_addr = mock_listener.local_addr().unwrap();
    tokio::spawn(async move {
        axum::serve(mock_listener, mock_shipping_app).await.unwrap();
    });

    let settings = Settings {
        db_url,
        server_addr: "0.0.0.0:8082".into(),
        shipping_url: format!("http://{}/quote", mock_addr),
    };

    let app = inventory_rs::root_router(db_pool, &settings);

    // 1. Test successful reservation
    let payload = serde_json::json!({
        "order_id": "0191234a-5b6c-7123-9000-000000000001",
        "product_id": product_id,
        "items_count": 2
    });

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/reserve")
                .header("Content-Type", "application/json")
                .body(Body::from(payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let body_json: serde_json::Value = serde_json::from_slice(&body).unwrap();

    assert_eq!(
        body_json["order_id"],
        "0191234a-5b6c-7123-9000-000000000001"
    );
    assert_eq!(body_json["items_reserved"], 2);
    assert_eq!(body_json["status"], "RESERVED");
    assert!(body_json["reservation_id"].is_string());

    // 2. Test invalid items_count <= 0 -> 400 Bad Request
    let invalid_payload = serde_json::json!({
        "order_id": "0191234a-5b6c-7123-9000-000000000002",
        "product_id": product_id,
        "items_count": -5
    });

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/reserve")
                .header("Content-Type", "application/json")
                .body(Body::from(invalid_payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);

    // 3. Test insufficient stock -> 409 Conflict
    let out_of_stock_payload = serde_json::json!({
        "order_id": "0191234a-5b6c-7123-9000-000000000003",
        "product_id": product_id,
        "items_count": 1000
    });

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/reserve")
                .header("Content-Type", "application/json")
                .body(Body::from(out_of_stock_payload.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::CONFLICT);
}
