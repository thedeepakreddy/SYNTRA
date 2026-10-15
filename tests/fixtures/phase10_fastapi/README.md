# Phase 10 controlled customer repository

The defect is in `validate_quantity`: it rejects negative quantities but accepts
zero. The approved behavior is HTTP 422 for nonpositive or noninteger quantities,
and HTTP 200 with the supplied quantity for positive integers. The initial tests
omit zero. SYNTRA must inspect source, add a regression test, correct validation,
run tests in Docker and submit the actual patch for independent role review.

The fixture is copied into a temporary Git repository with its own history. It is
never used as the SYNTRA platform's frontend or as a production deployment.
