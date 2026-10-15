FROM python:3.12-alpine

# Install git, bash, shadow (for useradd/groupadd), coreutils
RUN apk add --no-cache git bash shadow coreutils

# Create non-root user 'syntra' with UID 1000 and GID 1000
RUN groupadd -g 1000 syntra && \
    useradd -u 1000 -g syntra -m -s /bin/bash syntra

# Create workspace
WORKDIR /workspace
RUN chown -R syntra:syntra /workspace

USER syntra
