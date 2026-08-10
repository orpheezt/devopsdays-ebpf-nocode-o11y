mod common;

use axum::{Json, Router, http::StatusCode, routing::get};
use inventory_rs::inventory::Inventory;
use inventory_rs::reservations::{
    Reservation, ReservationError, ReservationService,
    schemas::{ReserveItem, ReserveRequest},
};
use uuid::Uuid;

async fn start_mock_shipping_server(router: Router) -> String {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
        .await
        .expect("Failed to bind ephemeral port for mock shipping server");
    let addr = listener.local_addr().expect("Failed to get local address");
    tokio::spawn(async move {
        axum::serve(listener, router).await.unwrap();
    });
    format!("http://{}/quote", addr)
}

#[tokio::test]
async fn test_reserve_invalid_input() {
    let (_container, _db_url, db_pool) = common::setup_test_db().await;

    let service = ReservationService {
        db_pool,
        http_client: reqwest::Client::new(),
        shipping_url: "http://127.0.0.1:8084/quote".to_string(),
    };

    // Test items_count = 0
    let payload_zero = ReserveRequest {
        order_id: Uuid::now_v7(),
        product_id: None,
        items_count: None,
        items: vec![ReserveItem {
            product_id: Uuid::now_v7(),
            quantity: 0,
        }],
    };
    let result = service.reserve(payload_zero).await;
    assert!(matches!(result, Err(ReservationError::InvalidInput(_))));
    if let Err(ReservationError::InvalidInput(msg)) = result {
        assert_eq!(msg, "items_count must be greater than 0");
    }

    // Test negative items_count
    let payload_negative = ReserveRequest {
        order_id: Uuid::now_v7(),
        product_id: None,
        items_count: None,
        items: vec![ReserveItem {
            product_id: Uuid::now_v7(),
            quantity: -10,
        }],
    };
    let result_neg = service.reserve(payload_negative).await;
    assert!(matches!(result_neg, Err(ReservationError::InvalidInput(_))));
}

#[tokio::test]
async fn test_reserve_product_not_found() {
    let (_container, _db_url, db_pool) = common::setup_test_db().await;

    let service = ReservationService {
        db_pool,
        http_client: reqwest::Client::new(),
        shipping_url: "http://127.0.0.1:8084/quote".to_string(),
    };

    let missing_product_id = Uuid::now_v7();
    let payload = ReserveRequest {
        order_id: Uuid::now_v7(),
        product_id: None,
        items_count: None,
        items: vec![ReserveItem {
            product_id: missing_product_id,
            quantity: 2,
        }],
    };

    let result = service.reserve(payload).await;
    assert!(
        matches!(result, Err(ReservationError::ProductNotFound(id)) if id == missing_product_id)
    );
}

#[tokio::test]
async fn test_reserve_insufficient_stock() {
    let (_container, _db_url, db_pool) = common::setup_test_db().await;
    let mut db = db_pool.clone();

    let created = toasty::create!(Inventory {
        product_id: Uuid::now_v7(),
        product_name: "Low Stock Item".to_string(),
        stock_quantity: 3,
        reserved_quantity: 0,
    })
    .exec(&mut db)
    .await
    .expect("Failed to create inventory item");
    let product_id = created.product_id;

    let service = ReservationService {
        db_pool,
        http_client: reqwest::Client::new(),
        shipping_url: "http://127.0.0.1:8084/quote".to_string(),
    };

    let payload = ReserveRequest {
        order_id: Uuid::now_v7(),
        product_id: Some(product_id),
        items_count: Some(5),
        items: vec![],
    };

    let result = service.reserve(payload).await;
    match result {
        Err(ReservationError::InsufficientStock {
            product_id: pid,
            requested,
            available,
        }) => {
            assert_eq!(pid, product_id);
            assert_eq!(requested, 5);
            assert_eq!(available, 3);
        }
        other => panic!("Expected InsufficientStock error, got {:?}", other),
    }
}

#[tokio::test]
async fn test_reserve_shipping_service_unreachable() {
    let (_container, _db_url, db_pool) = common::setup_test_db().await;
    let mut db = db_pool.clone();

    let created = toasty::create!(Inventory {
        product_id: Uuid::now_v7(),
        product_name: "Test Item".to_string(),
        stock_quantity: 50,
        reserved_quantity: 0,
    })
    .exec(&mut db)
    .await
    .expect("Failed to create inventory item");
    let product_id = created.product_id;

    // Point to an unused local port where no server is running
    let service = ReservationService {
        db_pool,
        http_client: reqwest::Client::new(),
        shipping_url: "http://127.0.0.1:59999/quote".to_string(),
    };

    let payload = ReserveRequest {
        order_id: Uuid::now_v7(),
        product_id: Some(product_id),
        items_count: Some(2),
        items: vec![],
    };

    let result = service.reserve(payload).await;
    assert!(matches!(
        result,
        Err(ReservationError::ShippingServiceUnavailable(_))
    ));
}

#[tokio::test]
async fn test_reserve_shipping_service_error_status() {
    let (_container, _db_url, db_pool) = common::setup_test_db().await;
    let mut db = db_pool.clone();

    let created = toasty::create!(Inventory {
        product_id: Uuid::now_v7(),
        product_name: "Test Item".to_string(),
        stock_quantity: 50,
        reserved_quantity: 0,
    })
    .exec(&mut db)
    .await
    .expect("Failed to create inventory item");
    let product_id = created.product_id;

    // Mock shipping server returning 500 Internal Server Error
    let mock_app = Router::new().route(
        "/quote",
        get(|| async { StatusCode::INTERNAL_SERVER_ERROR }),
    );
    let shipping_url = start_mock_shipping_server(mock_app).await;

    let service = ReservationService {
        db_pool,
        http_client: reqwest::Client::new(),
        shipping_url,
    };

    let payload = ReserveRequest {
        order_id: Uuid::now_v7(),
        product_id: Some(product_id),
        items_count: Some(2),
        items: vec![],
    };

    let result = service.reserve(payload).await;
    assert!(matches!(
        result,
        Err(ReservationError::ShippingServiceUnavailable(_))
    ));
}

#[tokio::test]
async fn test_reserve_shipping_service_invalid_json() {
    let (_container, _db_url, db_pool) = common::setup_test_db().await;
    let mut db = db_pool.clone();

    let created = toasty::create!(Inventory {
        product_id: Uuid::now_v7(),
        product_name: "Test Item".to_string(),
        stock_quantity: 50,
        reserved_quantity: 0,
    })
    .exec(&mut db)
    .await
    .expect("Failed to create inventory item");
    let product_id = created.product_id;

    // Mock shipping server returning 200 OK with non-JSON body
    let mock_app = Router::new().route("/quote", get(|| async { "invalid json text" }));
    let shipping_url = start_mock_shipping_server(mock_app).await;

    let service = ReservationService {
        db_pool,
        http_client: reqwest::Client::new(),
        shipping_url,
    };

    let payload = ReserveRequest {
        order_id: Uuid::now_v7(),
        product_id: Some(product_id),
        items_count: Some(2),
        items: vec![],
    };

    let result = service.reserve(payload).await;
    assert!(matches!(
        result,
        Err(ReservationError::ShippingServiceUnavailable(_))
    ));
}

#[tokio::test]
async fn test_reserve_success() {
    let (_container, _db_url, db_pool) = common::setup_test_db().await;
    let mut db = db_pool.clone();

    let created = toasty::create!(Inventory {
        product_id: Uuid::now_v7(),
        product_name: "Valid Widget".to_string(),
        stock_quantity: 100,
        reserved_quantity: 10,
    })
    .exec(&mut db)
    .await
    .expect("Failed to create inventory item");
    let product_id = created.product_id;

    // Mock shipping server returning valid quote
    let mock_app = Router::new().route(
        "/quote",
        get(|| async {
            Json(serde_json::json!({
                "carrier": "FedEx Express",
                "cost": 24.99,
                "est_days": 1
            }))
        }),
    );
    let shipping_url = start_mock_shipping_server(mock_app).await;

    let service = ReservationService {
        db_pool: db_pool.clone(),
        http_client: reqwest::Client::new(),
        shipping_url,
    };

    let order_id = Uuid::now_v7();
    let payload = ReserveRequest {
        order_id,
        product_id: None,
        items_count: None,
        items: vec![ReserveItem {
            product_id,
            quantity: 15,
        }],
    };

    let response = service
        .reserve(payload)
        .await
        .expect("Reservation should succeed");

    // Verify response fields
    assert_eq!(response.order_id, order_id);
    assert_eq!(response.items_reserved, 15);
    assert_eq!(response.status, "RESERVED");
    assert_eq!(response.shipping_info.carrier, "FedEx Express");
    assert_eq!(response.shipping_info.cost, 24.99);
    assert_eq!(response.shipping_info.est_days, 1);

    // Verify DB state: inventory updated
    let updated_item = Inventory::get_by_product_id(&mut db, &product_id)
        .await
        .expect("Inventory item should exist");

    assert_eq!(updated_item.stock_quantity, 85); // 100 - 15
    assert_eq!(updated_item.reserved_quantity, 25); // 10 + 15

    // Verify DB state: reservation record created
    let reservation = Reservation::get_by_reservation_id(&mut db, &response.reservation_id)
        .await
        .expect("Reservation record should exist in DB");

    assert_eq!(reservation.order_id, order_id);
    assert_eq!(reservation.items_count, 15);
    assert_eq!(reservation.status, "RESERVED");
}

#[tokio::test]
async fn test_reserve_multi_item_cart_success() {
    let (_container, _db_url, db_pool) = common::setup_test_db().await;
    let mut db = db_pool.clone();

    let p1 = toasty::create!(Inventory {
        product_id: Uuid::now_v7(),
        product_name: "Item 1".to_string(),
        stock_quantity: 20,
        reserved_quantity: 0,
    })
    .exec(&mut db)
    .await
    .unwrap();

    let p2 = toasty::create!(Inventory {
        product_id: Uuid::now_v7(),
        product_name: "Item 2".to_string(),
        stock_quantity: 30,
        reserved_quantity: 5,
    })
    .exec(&mut db)
    .await
    .unwrap();

    let mock_app = Router::new().route(
        "/quote",
        get(|| async {
            Json(serde_json::json!({
                "carrier": "DHL Express",
                "cost": 15.00,
                "est_days": 2
            }))
        }),
    );
    let shipping_url = start_mock_shipping_server(mock_app).await;

    let service = ReservationService {
        db_pool: db_pool.clone(),
        http_client: reqwest::Client::new(),
        shipping_url,
    };

    let order_id = Uuid::now_v7();
    let payload = ReserveRequest {
        order_id,
        product_id: None,
        items_count: None,
        items: vec![
            ReserveItem {
                product_id: p1.product_id,
                quantity: 4,
            },
            ReserveItem {
                product_id: p2.product_id,
                quantity: 10,
            },
        ],
    };

    let response = service
        .reserve(payload)
        .await
        .expect("Multi-item reservation should succeed");

    assert_eq!(response.order_id, order_id);
    assert_eq!(response.items_reserved, 14); // 4 + 10

    let item1 = Inventory::get_by_product_id(&mut db, &p1.product_id)
        .await
        .unwrap();
    assert_eq!(item1.stock_quantity, 16);
    assert_eq!(item1.reserved_quantity, 4);

    let item2 = Inventory::get_by_product_id(&mut db, &p2.product_id)
        .await
        .unwrap();
    assert_eq!(item2.stock_quantity, 20);
    assert_eq!(item2.reserved_quantity, 15);
}
