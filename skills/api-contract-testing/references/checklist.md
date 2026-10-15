# Api-Contract-Testing Checklist

- [ ] All responses must adhere strictly to declared OpenAPI schemas.
- [ ] Breaking changes (removed fields, altered types, new required request fields) must be flagged as drift.
- [ ] Error responses must validate against RFC 7807 Problem Details schemas.
