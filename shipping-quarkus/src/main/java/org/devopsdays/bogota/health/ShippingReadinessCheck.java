package org.devopsdays.bogota.health;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.devopsdays.bogota.service.RateCalculatorService;
import org.eclipse.microprofile.health.HealthCheck;
import org.eclipse.microprofile.health.HealthCheckResponse;
import org.eclipse.microprofile.health.Readiness;

@Readiness
@ApplicationScoped
public class ShippingReadinessCheck implements HealthCheck {

    @Inject
    RateCalculatorService rateCalculatorService;

    @Override
    public HealthCheckResponse call() {
        if (rateCalculatorService.isHealthy()) {
            return HealthCheckResponse.named("shipping-quarkus-readiness")
                    .up()
                    .withData("rate_tables_loaded", true)
                    .build();
        }
        return HealthCheckResponse.named("shipping-quarkus-readiness")
                .down()
                .withData("rate_tables_loaded", false)
                .build();
    }
}
