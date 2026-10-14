# Skill: Integration Testing

## Overview
Test end-to-end flows involving real databases, Redis queues, and local MinIO storage.

## Methodology
1. **Real Infrastructure**: Test against running Compose services where appropriate.
2. **State Cleanup**: Ensure tests clean up databases or run inside isolated transactions.
3. **Asynchronous Verification**: Test async message delivery and event stream ordering.
