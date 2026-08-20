# Single-instance unhealthy diagnosis

When one instance is unhealthy, compare its logs with a healthy peer. A repeated startup failure on the unhealthy instance can explain a subset of HTTP 500 responses while the overall service remains partially available.

The diagnosis should distinguish an isolated instance problem from a fleet-wide deployment defect.