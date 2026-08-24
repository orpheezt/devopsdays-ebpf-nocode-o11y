CREATE TABLE "reservations" (
    "reservation_id" UUID NOT NULL,
    "order_id" UUID NOT NULL,
    "items_count" INTEGER NOT NULL,
    "status" TEXT NOT NULL,
    PRIMARY KEY ("reservation_id")
);
CREATE TABLE "inventories" (
    "product_id" UUID NOT NULL,
    "product_name" TEXT NOT NULL,
    "stock_quantity" INTEGER NOT NULL,
    "reserved_quantity" INTEGER NOT NULL,
    PRIMARY KEY ("product_id")
);
INSERT INTO "inventories" ("product_id", "product_name", "stock_quantity", "reserved_quantity")
VALUES
    ('0191234a-5b6c-7123-9000-000000000000', 'DevOpsDays T-Shirt', 1000, 0),
    ('0191234a-5b6c-7123-9000-000000000001', 'eBPF Observability Sticker Pack', 500, 0),
    ('0191234a-5b6c-7123-9000-000000000002', 'Cloud Native Coffee Mug', 250, 0)
ON CONFLICT ("product_id") DO NOTHING;

