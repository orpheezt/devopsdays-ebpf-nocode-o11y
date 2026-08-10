use testcontainers_modules::postgres::Postgres;
use testcontainers_modules::testcontainers::runners::AsyncRunner;
use testcontainers_modules::testcontainers::ContainerAsync;
use testcontainers_modules::testcontainers::ImageExt;

pub fn run_migrations(db_url: &str) {
    let status = std::process::Command::new("cargo")
        .args(["run", "--bin", "migrations", "--", "migration", "apply"])
        .env("DATABASE_URL", db_url)
        .status()
        .expect("Failed to execute migrations CLI via std::process::Command");

    assert!(status.success(), "Database migration failed");
}

pub async fn setup_test_db() -> (ContainerAsync<Postgres>, String, toasty::Db) {
    let container = Postgres::default()
        .with_tag("18.4-trixie")
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

    run_migrations(&db_url);

    let db_pool = inventory_rs::db::get_db_pool(inventory_rs::db::DbConfig {
        url: db_url.clone(),
    })
    .await
    .expect("Failed to connect to DB");

    (container, db_url, db_pool)
}
