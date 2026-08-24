package org.devopsdays.bogota;

import io.quarkus.test.junit.QuarkusTest;
import io.restassured.http.ContentType;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.Matchers.*;

@QuarkusTest
class ShippingResourceTest {

    @Test
    @DisplayName("GET /quote with default parameters returns domestic Colombia 1-item rate")
    void testDefaultQuoteEndpoint() {
        given()
            .when().get("/quote")
            .then()
                .statusCode(200)
                .contentType(ContentType.JSON)
                .body("carrier", is("DHL / Servientrega"))
                .body("cost", is(12.50f))
                .body("est_days", is(2));
    }

    @Test
    @DisplayName("GET /quote with explicit destination_country and items_count computes customized rate")
    void testCustomDestinationAndItemsCount() {
        given()
            .queryParam("destination_country", "US")
            .queryParam("items_count", 2)
            .when().get("/quote")
            .then()
                .statusCode(200)
                .contentType(ContentType.JSON)
                .body("carrier", is("FedEx International"))
                .body("cost", is(36.00f)) // 24.00 base + 2 * 6.00
                .body("est_days", is(3));
    }

    @Test
    @DisplayName("GET /quote with volume order applies bulk discount")
    void testVolumeOrderQuote() {
        given()
            .queryParam("destination_country", "MX")
            .queryParam("items_count", 5)
            .when().get("/quote")
            .then()
                .statusCode(200)
                .contentType(ContentType.JSON)
                .body("carrier", is("DHL Express / LATAM"))
                .body("cost", is(40.95f)) // (18.00 base + 5 * 5.50) * 0.90 = 45.50 * 0.90 = 40.95
                .body("est_days", is(3));
    }

    @Test
    @DisplayName("GET /quote strictly returns the 3 contract fields expected by inventory-rs")
    void testStrictContractFields() {
        given()
            .when().get("/quote")
            .then()
                .statusCode(200)
                .body("$", hasKey("carrier"))
                .body("$", hasKey("cost"))
                .body("$", hasKey("est_days"));
    }
}
