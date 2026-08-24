INSERT INTO "inventories" ("product_id", "product_name", "stock_quantity", "reserved_quantity")
VALUES
    ('0191234a-5b6c-7123-9000-000000000000', 'DevOpsDays T-Shirt', 1000, 0),
    ('0191234a-5b6c-7123-9000-000000000001', 'eBPF Observability Sticker Pack', 500, 0),
    ('0191234a-5b6c-7123-9000-000000000002', 'Cloud Native Coffee Mug', 250, 0),
    ('0191234a-5b6c-7123-9000-000000000003', 'OpenTelemetry Stainless Water Bottle', 300, 0),
    ('0191234a-5b6c-7123-9000-000000000004', 'Kubernetes Operator Hoodie', 150, 0)
ON CONFLICT ("product_id") DO NOTHING;
