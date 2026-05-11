# @sovereign-shield/sdk

Shared TypeScript API client for Sovereign Shield web, desktop, and mobile consoles.

Responsibilities:

- API abstraction
- login and refresh-token rotation
- device session metadata
- shared RBAC helpers
- client audit event helper
- pluggable secure storage adapters

The SDK does not enforce security decisions. FastAPI remains the enforcement point.
