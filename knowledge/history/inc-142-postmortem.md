# INC-142 historical incident

INC-142 affected `checkout-api` after a release when `PaymentGatewayClient` initialization failed on one instance. The incident was identified by correlating startup logs, instance health, deployment metadata, and intermittent checkout errors.

The historical pattern is a useful comparison, not proof that a current incident has the same cause.