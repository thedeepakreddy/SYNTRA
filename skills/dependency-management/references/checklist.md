# Dependency-Management Checklist

- [ ] All production dependencies must be pinned to exact semantic versions.
- [ ] Lockfiles (`uv.lock`) must remain synchronized with manifests (`pyproject.toml`).
- [ ] Zero dependencies with known High or Critical CVEs may be introduced.
