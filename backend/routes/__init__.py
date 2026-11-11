"""HTTP routes, one APIRouter module per domain. Each module's build() receives the service (and the auth
dependency where needed) and returns its router; api.create_app() includes them in order."""
