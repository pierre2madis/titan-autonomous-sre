# Security and Publication Constraints

## Development security

- Bind API and frontend to loopback interfaces
- Access remotely through an authenticated SSH tunnel
- Keep database credentials outside source control
- Avoid logging credentials or connection secrets
- Use read-only database sessions for evidence queries
- Do not commit Kafka offsets from monitoring collectors

## Publication exclusions

Never publish:

- .env files
- Passwords or tokens
- Private keys
- Python virtual environments
- node_modules
- Database dumps
- Local incident evidence containing sensitive data
- Internal network configuration
- Machine-specific configuration files

## Production gaps

Before production deployment, implement:

- Authentication
- Role-based authorization
- TLS termination
- Secret management
- Network access restrictions
- Audit logging
- Operational service supervision
- Failure and recovery testing
