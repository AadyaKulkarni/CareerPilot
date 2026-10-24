# Horizontal scaling notes

The API is stateless: authentication uses signed JWTs, persistent state lives in PostgreSQL, and Redis is available for shared caching/background jobs. This means multiple backend containers can run behind a load balancer.

Example production topology:

Internet -> Load Balancer -> API replicas (N) -> PostgreSQL / Redis / Object Storage

Recommended next steps for production:
- Put PostgreSQL behind a managed HA service.
- Use PgBouncer/connection pooling.
- Run 2+ API replicas behind Nginx, an ingress controller, or a cloud load balancer.
- Move resume files to S3-compatible object storage.
- Add Celery/RQ/Arq workers using Redis for PDF parsing, ML inference, and LLM jobs.
- Add Prometheus/Grafana/OpenTelemetry.
- Use Kubernetes HPA or ECS/Kubernetes service autoscaling.
- Store `SECRET_KEY` and provider credentials in a secret manager.
