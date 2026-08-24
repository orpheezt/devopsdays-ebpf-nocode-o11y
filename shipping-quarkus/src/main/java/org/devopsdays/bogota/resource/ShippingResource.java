package org.devopsdays.bogota.resource;

import jakarta.inject.Inject;
import jakarta.ws.rs.DefaultValue;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.QueryParam;
import jakarta.ws.rs.core.MediaType;
import org.devopsdays.bogota.dto.ShippingQuoteResponse;
import org.devopsdays.bogota.service.RateCalculatorService;
import org.jboss.logging.Logger;

@Path("/quote")
public class ShippingResource {

    private static final Logger LOG = Logger.getLogger(ShippingResource.class);

    @Inject
    RateCalculatorService rateCalculatorService;

    @GET
    @Produces(MediaType.APPLICATION_JSON)
    public ShippingQuoteResponse getQuote(
        @QueryParam("destination_country") @DefaultValue("CO") String destinationCountry,
        @QueryParam("items_count") @DefaultValue("1") int itemsCount
    ) {
        ShippingQuoteResponse response = rateCalculatorService.calculateQuote(destinationCountry, itemsCount);
        LOG.infof("Shipping quote computed: country=%s, items=%d -> carrier=%s, cost=%.2f, days=%d",
                destinationCountry, itemsCount, response.carrier(), response.cost(), response.estDays());
        return response;
    }
}
