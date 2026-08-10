use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use inventory_rs::Settings;
use testcontainers_modules::postgres::Postgres;
use testcontainers_modules::testcontainers::runners::AsyncRunner;
use tower::ServiceExt;

#[tokio::test]
async fn test_health_check_endpoint() {
    let container = Postgres::default()
        .start()
        .await
        .expect("Failed to start Postgres container");
    let host_port = container
        .get_host_port_ipv4(5432)
        .await
        .expect("Failed to get port");
    let db_url = format!(
        "postgres://postgres:postgres@127.0.0.1:{}/postgres",
        host_port
    );

    let db_pool = inventory_rs::db::get_db_pool(inventory_rs::db::DbConfig {
        url: db_url.clone(),
    })
    .await
    .expect("Failed to connect to DB");

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
    let container = Postgres::default()
        .start()
        .await
        .expect("Failed to start Postgres container");
    let host_port = container
        .get_host_port_ipv4(5432)
        .await
        .expect("Failed to get port");
    let db_url = format!(
        "postgres://postgres:postgres@127.0.0.1:{}/postgres",
        host_port
    );

    let db_pool = inventory_rs::db::get_db_pool(inventory_rs::db::DbConfig {
        url: db_url.clone(),
    })
    .await
    .expect("Failed to connect to DB");

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

    let payload = serde_json::json!({
        "order_id": "0191234a-5b6c-7123-9000-000000000001",
        "items_count": 2
    });

    let response = app
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
    assert!(
        !body_json["reservation_id"]
            .as_str()
            .unwrap()
            .starts_with("RES-")
    );
}
