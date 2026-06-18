# Database

## Database Engine
PostgreSQL

## Main Tables
- `users`: Stores OAuth user information.
- `clientes`: Stores customer records.
- `sessoes`: Stores tattoo sessions.
- `historico_pagamentos`: Stores payment records.
- `historico_gastos`: Stores expenses.
- `inventory`: Stores inventory items.
- `extrato`: Stores monthly financial statements.

## Relationships

```text
Cliente
   │
   └── Sessões

Sessões
   │
   └── Pagamentos
```

## Local Database Access
```bash
docker-compose exec db psql -U admin -d tattoo_studio
```

## Backup
```bash
docker-compose exec db pg_dump -U admin tattoo_studio > backup.sql
```

## Restore
```bash
docker-compose exec -T db psql -U admin tattoo_studio < backup.sql
```