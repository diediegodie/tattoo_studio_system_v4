# Architecture

## Overview

The Tattoo Studio Management System follows a layered architecture designed to separate business logic, data access, and presentation concerns.

```text
Frontend (Jinja2 + JS)
        │
        ▼
Controllers
        │
        ▼
Services
        │
        ▼
Repositories
        │
        ▼
PostgreSQL
```

## Application Layers

### Controllers

Responsible for:

HTTP request handling
Input validation
Authentication checks
Response formatting
Location:
backend/app/controllers/

### Services

Responsible for:
Business rules
Financial calculations
Session processing
Inventory operations
Location:
backend/app/services/

### Repositories

Responsible for:
Database communication
Query abstraction
Data persistence
Location:
backend/app/repositories/

### Models

SQLAlchemy ORM entities.
Location:
backend/app/models/

### External Integrations

#### Google OAuth
Authentication provider.
#### Google Calendar
Appointment synchronization.
#### JotForm
Automatic client intake.

### Design Principles
Separation of concerns Repository pattern Service layer architecture Dependency isolation Testability