package org.devopsdays.bogota;

import io.quarkus.test.junit.QuarkusTest;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.Matchers.hasKey;

@QuarkusTest
class ShippingHealthTest {

    @Test
    @DisplayName("GET /livez returns HTTP 200 with status UP and service identification")
    void testLivenessProbe() {
        given()
            .when().get("/livez")
            .then()
                .statusCode(200)
                .body("status", is("UP"))
                .body("checks[0].name", is("shipping-quarkus-liveness"))
                .body("checks[0].status", is("UP"))
                .body("checks[0].data.service", is("shipping-quarkus"));
    }

    @Test
    @DisplayName("GET /readyz returns HTTP 200 with status UP and rate_tables_loaded flag")
    void testReadinessProbe() {
        given()
            .when().get("/readyz")
            .then()
                .statusCode(200)
                .body("status", is("UP"))
                .body("checks[0].name", is("shipping-quarkus-readiness"))
                .body("checks[0].status", is("UP"))
                .body("checks[0].data.rate_tables_loaded", is(true));
    }
}
