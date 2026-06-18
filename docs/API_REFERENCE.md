# API Reference
## Authentication
#### Login

```http
POST /auth/login
```

#### Logout

```http
POST /auth/logout
```

## Clients
#### List Clients

```http
GET /clients/api/list
```

#### Create Client

```http
POST /clients/
```

#### Update Client

```http
PUT /clients/<id>
```

#### Delete Client

```http
DELETE /clients/<id>
```

## Sessions
#### List Sessions

```http
GET /api/sessoes
```

#### Create Session

```http
POST /api/sessoes
```

#### Update Session

```http
PUT /api/sessoes/<id>
```

#### Delete Session

```http
DELETE /api/sessoes/<id>
```

## Inventory
#### List Inventory

```http
GET /api/inventory
```
#### Create Item

```http
POST /inventory/
```
#### Update Item

```http
PUT /inventory/<id>
```
#### Delete Item

```http
DELETE /inventory/<id>
```

## Financial
#### Monthly Statement

```http
GET /api/financeiro/extrato/<year>/<month>
```

#### Trigger Statement Generation

```http
POST /admin/extrato/trigger
```
