# PaymentGatewayClient dependency overview

`PaymentGatewayClient` is initialized during application startup. Configuration and network initialization failures can prevent one instance from becoming ready even when other instances remain healthy.

When investigating a checkout failure, correlate dependency initialization messages with instance identity and deployment timing. Avoid treating a dependency name alone as proof of root cause.