# Checkout API service overview

`checkout-api` handles checkout requests and uses `PaymentGatewayClient` during startup to validate payment connectivity. Each instance reports health independently. A single unhealthy instance can still cause intermittent failures when the load balancer routes requests to it.

The service is deployed as versioned releases. Deployment metadata confirms what was released, but does not by itself prove that every instance completed initialization.