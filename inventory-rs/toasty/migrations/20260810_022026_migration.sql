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

