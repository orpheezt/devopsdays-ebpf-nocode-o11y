package org.devopsdays.bogota.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record ShippingQuoteResponse(
    String carrier,
    double cost,
    @JsonProperty("est_days") int estDays
) {}
