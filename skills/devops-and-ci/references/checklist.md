# Devops-And-Ci Checklist

- [ ] All containers must run as non-root users with explicit UID/GID.
- [ ] Container builds must use multi-stage Dockerfiles to minimize image attack surface.
- [ ] Health check probes and resource limits must be declared for all Compose services.
