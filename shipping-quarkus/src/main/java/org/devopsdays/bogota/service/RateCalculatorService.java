package org.devopsdays.bogota.service;

import jakarta.enterprise.context.ApplicationScoped;
import org.devopsdays.bogota.dto.ShippingQuoteResponse;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@ApplicationScoped
public class RateCalculatorService {

    private final Map<String, CarrierConfig> rateTables = new ConcurrentHashMap<>();

    public RateCalculatorService() {
        rateTables.put("CO", new CarrierConfig("DHL / Servientrega", 8.50, 4.00, 2));
        rateTables.put("LATAM", new CarrierConfig("DHL Express / LATAM", 18.00, 5.50, 3));
        rateTables.put("US", new CarrierConfig("FedEx International", 24.00, 6.00, 3));
        rateTables.put("GLOBAL", new CarrierConfig("DHL Express Worldwide", 35.00, 8.00, 5));
    }

    public boolean isHealthy() {
        return !rateTables.isEmpty();
    }

    public ShippingQuoteResponse calculateQuote(String country, int itemsCount) {
        String normalizedCountry = (country == null || country.isBlank()) ? "CO" : country.trim().toUpperCase();
        int normalizedItems = Math.max(1, Math.min(itemsCount, 1000));

        CarrierConfig config = switch (normalizedCountry) {
            case "CO", "COL" -> rateTables.get("CO");
            case "MX", "BR", "CL", "AR", "PE", "EC", "PA" -> rateTables.get("LATAM");
            case "US", "USA", "CA", "CAN" -> rateTables.get("US");
            default -> rateTables.get("GLOBAL");
        };

        double discountMultiplier = (normalizedItems >= 10) ? 0.80 : (normalizedItems >= 5) ? 0.90 : 1.0;
        double subtotal = config.baseRate() + (config.perItemRate() * normalizedItems);
        double finalCost = BigDecimal.valueOf(subtotal * discountMultiplier)
                .setScale(2, RoundingMode.HALF_UP)
                .doubleValue();

        return new ShippingQuoteResponse(
            config.carrierName(),
            finalCost,
            config.estimatedTransitDays()
        );
    }
}
