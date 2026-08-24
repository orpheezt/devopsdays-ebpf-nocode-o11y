package org.devopsdays.bogota.service;

import org.devopsdays.bogota.dto.ShippingQuoteResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import static org.junit.jupiter.api.Assertions.*;

class RateCalculatorServiceTest {

    private RateCalculatorService service;

    @BeforeEach
    void setUp() {
        service = new RateCalculatorService();
    }

    @Test
    @DisplayName("isHealthy returns true when rate tables are initialized")
    void testIsHealthy() {
        assertTrue(service.isHealthy());
    }

    @Test
    @DisplayName("Domestic Colombia quote for 1 item computes $12.50 with 2 days transit")
    void testDomesticColombiaQuoteSingleItem() {
        ShippingQuoteResponse quote = service.calculateQuote("CO", 1);
        assertNotNull(quote);
        assertEquals("DHL / Servientrega", quote.carrier());
        assertEquals(12.50, quote.cost(), 0.001);
        assertEquals(2, quote.estDays());
    }

    @Test
    @DisplayName("Domestic Colombia quote for 2 items computes $16.50 (8.50 base + 2 * 4.00)")
    void testDomesticColombiaQuoteMultipleItems() {
        ShippingQuoteResponse quote = service.calculateQuote("CO", 2);
        assertNotNull(quote);
        assertEquals("DHL / Servientrega", quote.carrier());
        assertEquals(16.50, quote.cost(), 0.001);
        assertEquals(2, quote.estDays());
    }

    @ParameterizedTest
    @ValueSource(strings = {"co", "CO", "COL", " col "})
    @DisplayName("Input normalization handles case variations and whitespace for Colombia")
    void testCountryNormalization(String countryInput) {
        ShippingQuoteResponse quote = service.calculateQuote(countryInput, 1);
        assertEquals("DHL / Servientrega", quote.carrier());
        assertEquals(12.50, quote.cost(), 0.001);
        assertEquals(2, quote.estDays());
    }

    @ParameterizedTest
    @ValueSource(strings = {"MX", "BR", "CL", "AR", "PE", "EC", "PA"})
    @DisplayName("LATAM region countries use DHL Express / LATAM with 3 days transit")
    void testLatamRegionQuotes(String country) {
        ShippingQuoteResponse quote = service.calculateQuote(country, 1);
        assertEquals("DHL Express / LATAM", quote.carrier());
        assertEquals(23.50, quote.cost(), 0.001); // 18.00 base + 5.50
        assertEquals(3, quote.estDays());
    }

    @ParameterizedTest
    @ValueSource(strings = {"US", "USA", "CA", "CAN"})
    @DisplayName("North America region countries use FedEx International with 3 days transit")
    void testNorthAmericaQuotes(String country) {
        ShippingQuoteResponse quote = service.calculateQuote(country, 1);
        assertEquals("FedEx International", quote.carrier());
        assertEquals(30.00, quote.cost(), 0.001); // 24.00 base + 6.00
        assertEquals(3, quote.estDays());
    }

    @ParameterizedTest
    @ValueSource(strings = {"DE", "FR", "JP", "GB", "AU", "UNKNOWN"})
    @DisplayName("Global region countries use DHL Express Worldwide with 5 days transit")
    void testGlobalRegionQuotes(String country) {
        ShippingQuoteResponse quote = service.calculateQuote(country, 1);
        assertEquals("DHL Express Worldwide", quote.carrier());
        assertEquals(43.00, quote.cost(), 0.001); // 35.00 base + 8.00
        assertEquals(5, quote.estDays());
    }

    @Test
    @DisplayName("5 to 9 items applies a 10% volume discount")
    void testVolumeDiscountTier1() {
        // CO: base 8.50 + 5 * 4.00 = 28.50 -> 10% discount = 28.50 * 0.90 = 25.65
        ShippingQuoteResponse quote = service.calculateQuote("CO", 5);
        assertEquals(25.65, quote.cost(), 0.001);
    }

    @Test
    @DisplayName("10+ items applies a 20% volume discount")
    void testVolumeDiscountTier2() {
        // CO: base 8.50 + 10 * 4.00 = 48.50 -> 20% discount = 48.50 * 0.80 = 38.80
        ShippingQuoteResponse quote = service.calculateQuote("CO", 10);
        assertEquals(38.80, quote.cost(), 0.001);
    }

    @Test
    @DisplayName("Invalid or negative items count is clamped to at least 1")
    void testNegativeOrZeroItemsClamped() {
        ShippingQuoteResponse quoteZero = service.calculateQuote("CO", 0);
        assertEquals(12.50, quoteZero.cost(), 0.001);

        ShippingQuoteResponse quoteNegative = service.calculateQuote("CO", -5);
        assertEquals(12.50, quoteNegative.cost(), 0.001);
    }

    @Test
    @DisplayName("Null or blank destination country defaults to Colombia (CO)")
    void testNullOrBlankCountryDefaultsToCo() {
        ShippingQuoteResponse quoteNull = service.calculateQuote(null, 1);
        assertEquals("DHL / Servientrega", quoteNull.carrier());
        assertEquals(12.50, quoteNull.cost(), 0.001);

        ShippingQuoteResponse quoteBlank = service.calculateQuote("   ", 1);
        assertEquals("DHL / Servientrega", quoteBlank.carrier());
        assertEquals(12.50, quoteBlank.cost(), 0.001);
    }
}
