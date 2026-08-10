CREATE TABLE "inventories" (
    "product_id" TEXT NOT NULL,
    "product_name" TEXT NOT NULL,
    "stock_quantity" INTEGER NOT NULL,
    "reserved_quantity" INTEGER NOT NULL,
    PRIMARY KEY ("product_id")
);
CREATE TABLE "reservations" (
    "reservation_id" TEXT NOT NULL,
    "order_id" TEXT NOT NULL,
    "items_count" INTEGER NOT NULL,
    "status" TEXT NOT NULL,
    PRIMARY KEY ("reservation_id")
);
