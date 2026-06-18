# Security

## Authentication

The system uses Google OAuth 2.0.

Authentication flow:

```text
User
 │
 ▼
Google OAuth
 │
 ▼
Application
 │
 ▼
Authorized Session
```

## Authorization

Authorization is email-based.

Example:

`AUTHORIZED_EMAILS=user@email.com`

Only authorized users can:

- Manage inventory
- Create sessions
- Register expenses
- Trigger financial operations

## JWT (JSON Web Token)

API endpoints use JWT tokens for stateless authentication.

Protected routes validate:
- Token signature
- Expiration
- Authorized email

## Security Features

- OAuth 2.0 for secure authentication
- JWT for stateless API authentication
- Rate limiting to prevent abuse
- HTTPS support for secure communication
- SQL injection protection via parameterized queries
- Secure session management with HTTP-only cookies
- Environment-based secrets for sensitive configuration

## 