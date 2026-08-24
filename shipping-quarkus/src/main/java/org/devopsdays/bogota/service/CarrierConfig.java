package org.devopsdays.bogota.service;

public record CarrierConfig(
    String carrierName,
    double baseRate,
    double perItemRate,
    int estimatedTransitDays
) {}
