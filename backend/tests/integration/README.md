# Integration Testing Framework

This directory contains comprehensive integration tests for the Tattoo Studio System, implementing Flask test client, database transaction isolation, and authentication fixtures following SOLID principles.

## Overview

The integration testing framework provides:

- **Flask Test Client**: Full HTTP endpoint testing with real Flask application context
- **Database Transaction Isolation**: Automatic rollback between tests for clean state
- **Authentication Fixtures**: Complete JWT and session authentication testing utilities
- **Performance Testing**: Load and performance testing capabilities
- **Security Testing**: Comprehensive security validation including XSS, CSRF, SQL injection protection

## Test Structure

### Integration Test Categories

- **Controller Integration**: Full HTTP request/response testing
- **Authentication Integration**: Complete authentication flow testing
- **Database Integration**: Transaction isolation and data consistency testing
- **Security Integration**: Security measure validation
- **Performance Integration**: Load and performance testing

### File Organization

```
tests/integration/
├── test_client_controller_integration.py    # Client controller integration tests
├── test_auth_controller_integration.py      # Authentication integration tests
└── README.md                               # This file

tests/fixtures/
├── integration_fixtures.py                 # Flask app, test client, database fixtures
├── auth_fixtures.py                       # Authentication and JWT fixtures
└── ...
```

## Fixtures Available

### Flask Application Fixtures

- `app`: Configured Flask application for testing
- `client`: Flask test client for HTTP requests
- `authenticated_client`: Test client with authentication helpers
- `runner`: Flask CLI test runner

### Database Fixtures

- `db_session`: Database session with automatic rollback
- `database_transaction_isolator`: Transaction isolation utilities
- `test_database`: Temporary test database

### Authentication Fixtures

- `valid_jwt_token`: Valid JWT token for testing
- `expired_jwt_token`: Expired JWT token for testing
- `invalid_jwt_token`: Invalid JWT token for testing
- `auth_headers_*`: Pre-configured authentication headers
- `mock_authenticated_user`: Mock user objects
- `authentication_scenarios`: Various authentication scenarios

### Testing Helpers

- `response_helper`: HTTP response testing utilities
- `auth_test_helper`: Authentication testing utilities
- `protected_endpoint_tester`: Automatic endpoint protection testing

## Usage Examples

### Basic Integration Test

```python
@pytest.mark.integration
@pytest.mark.controllers
def test_endpoint_integration(authenticated_client, response_helper):
    """Test endpoint with full integration."""
    response = authenticated_client.authenticated_get('/api/clients')
    
    json_data = response_helper.assert_json_response(response, 200)
    assert isinstance(json_data, list)
```

### Database Transaction Isolation

```python
@pytest.mark.integration
@pytest.mark.database
def test_with_database_isolation(db_session, database_transaction_isolator):
    """Test with database transaction isolation."""
    savepoint = database_transaction_isolator['create_savepoint']()
    
    try:
        # Database operations here
        # Will be automatically rolled back
        
        database_transaction_isolator['commit_savepoint'](savepoint)
    except Exception:
        database_transaction_isolator['rollback_to_savepoint'](savepoint)
        raise
```

### Authentication Testing

```python
@pytest.mark.integration
@pytest.mark.auth
def test_protected_endpoint(client, auth_headers_valid, auth_test_helper):
    """Test protected endpoint authentication."""
    # Test without auth
    response = client.get('/protected-endpoint')
    auth_test_helper.assert_requires_auth(response)
    
    # Test with auth
    response = client.get('/protected-endpoint', headers=auth_headers_valid)
    assert response.status_code == 200
```

### Performance Testing

```python
@pytest.mark.integration
@pytest.mark.performance
def test_endpoint_performance(authenticated_client):
    """Test endpoint performance."""
    import time
    
    start_time = time.time()
    response = authenticated_client.authenticated_get('/api/clients')
    end_time = time.time()
    
    assert (end_time - start_time) < 1.0  # Should respond within 1 second
    assert response.status_code == 200
```

## Running Integration Tests

### Run All Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ -m integration

# Run with verbose output
pytest tests/integration/ -m integration -v

# Run specific integration test categories
pytest tests/integration/ -m "integration and auth"
pytest tests/integration/ -m "integration and controllers"
pytest tests/integration/ -m "integration and database"
```

### Run Performance Tests

```bash
# Run performance tests
pytest tests/integration/ -m "integration and performance"

# Run with timing information
pytest tests/integration/ -m "integration and performance" --durations=10
```

### Run Security Tests

```bash
# Run security integration tests
pytest tests/integration/ -m "integration and security"
```

## Test Markers

Integration tests use the following markers:

- `@pytest.mark.integration`: Core integration test marker
- `@pytest.mark.auth`: Authentication-related tests
- `@pytest.mark.controllers`: Controller layer tests
- `@pytest.mark.database`: Database integration tests
- `@pytest.mark.security`: Security validation tests
- `@pytest.mark.performance`: Performance and load tests
- `@pytest.mark.flask`: Flask application context tests

## Database Transaction Isolation

The framework provides automatic database transaction isolation:

### How It Works

1. Each test gets a fresh database session
2. All database changes are wrapped in a transaction
3. The transaction is automatically rolled back after each test
4. Nested savepoints allow for complex transaction testing

### Benefits

- **Test Isolation**: Tests don't affect each other
- **Fast Execution**: No need to rebuild database between tests
- **Consistent State**: Each test starts with a clean database
- **Realistic Testing**: Uses real database transactions

### Usage

```python
def test_with_auto_rollback(db_session):
    """Database changes are automatically rolled back."""
    # Any database changes here will be rolled back automatically
    pass

def test_with_manual_savepoints(database_transaction_isolator):
    """Manual control over transaction savepoints."""
    savepoint = database_transaction_isolator['create_savepoint']()
    
    try:
        # Database operations
        database_transaction_isolator['commit_savepoint'](savepoint)
    except Exception:
        database_transaction_isolator['rollback_to_savepoint'](savepoint)
        raise
```

## Authentication Testing

### JWT Token Testing

The framework provides comprehensive JWT token testing:

- **Valid tokens**: For successful authentication tests
- **Expired tokens**: For token expiration testing
- **Invalid tokens**: For malformed token testing
- **Missing tokens**: For unauthenticated access testing

### Authentication Scenarios

Multiple authentication scenarios are provided:

- **Valid user**: Active user with proper permissions
- **Admin user**: Administrative user with elevated permissions
- **Inactive user**: Deactivated user account
- **Non-existent user**: User that doesn't exist in the system

### Session Management

The framework tests various session scenarios:

- **Valid sessions**: Properly authenticated sessions
- **Expired sessions**: Session timeout scenarios
- **Invalid sessions**: Corrupted or tampered sessions

## Security Testing

Integration tests include comprehensive security validation:

### Authentication Security

- JWT token validation
- Session hijacking protection
- Brute force protection
- Token expiration handling

### Input Validation

- SQL injection protection
- XSS prevention
- CSRF protection
- Input sanitization

### Access Control

- Endpoint authentication requirements
- Authorization level checking
- Resource access control

## Performance Testing

The framework includes performance testing capabilities:

### Response Time Testing

- Individual endpoint response times
- Concurrent request handling
- Load simulation

### Resource Usage

- Memory usage monitoring
- Database connection efficiency
- Session cleanup performance

## Best Practices

### Writing Integration Tests

1. **Use appropriate markers**: Mark tests with specific categories
2. **Test real scenarios**: Use realistic data and workflows
3. **Include error cases**: Test both success and failure scenarios
4. **Verify security**: Always test authentication and authorization
5. **Check performance**: Include performance assertions where relevant

### Database Testing

1. **Use transaction isolation**: Always use proper transaction management
2. **Test data consistency**: Verify data integrity across operations
3. **Test concurrent access**: Include concurrent operation tests
4. **Clean up properly**: Ensure proper cleanup of test data

### Authentication Testing

1. **Test all auth scenarios**: Include valid, invalid, and edge cases
2. **Verify security measures**: Test protection mechanisms
3. **Test token lifecycle**: Include creation, validation, and expiration
4. **Test session management**: Verify proper session handling

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure all dependencies are available
2. **Database connection**: Check test database configuration
3. **Flask context**: Ensure proper Flask application context
4. **Authentication setup**: Verify JWT secret and token configuration

### Debug Tips

1. Use `pytest -v` for verbose output
2. Use `pytest --tb=long` for detailed tracebacks
3. Add `pytest.set_trace()` for debugging breakpoints
4. Check fixture dependencies and import order

## Contributing

When adding new integration tests:

1. Follow SOLID principles in test design
2. Use appropriate fixtures and markers
3. Include comprehensive documentation
4. Test both success and failure scenarios
5. Verify performance and security aspects
6. Ensure proper transaction isolation
7. Update this README if adding new capabilities

## Future Enhancements

Planned improvements to the integration testing framework:

1. **API Contract Testing**: JSON schema validation
2. **Load Testing**: Comprehensive load testing utilities
3. **End-to-End Testing**: Browser automation integration
4. **Monitoring Integration**: Performance monitoring hooks
5. **CI/CD Integration**: Automated testing pipeline utilities
