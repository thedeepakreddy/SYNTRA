# Backend-Api-Development Checklist

- [ ] All endpoints must use Pydantic v2 models for request and response validation.
- [ ] All business logic must reside in domain services or entities, not in route handlers.
- [ ] Local unit tests must pass with 100% success inside the worker sandbox.
