# Testing Guide

This document describes the testing strategy and tools for the Tattoo Studio System.

## Overview

Our testing approach follows these principles:
- **Comprehensive Coverage**: Unit, integration, and security tests
- **Organized Structure**: Tests organized by functionality and type
- **Easy Execution**: Multiple ways to run tests for different scenarios
- **Quality Assurance**: Coverage reports and detailed output options

## Test Structure

```
tests/
├── conftest.py              # Central pytest configuration
├── unit/                    # Unit tests
│   └── test_auth_security.py
├── integration/             # Integration tests
└── fixtures/                # Test data and fixtures
```

## Test Categories

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests (isolated, fast)
- `@pytest.mark.integration` - Integration tests (database, services)
- `@pytest.mark.security` - Security-related tests 
- `@pytest.mark.auth` - Authentication and authorization tests

## Running Tests

### Quick Start

```bash
# Run all tests
python run_tests.py

# Run with verbose output
python run_tests.py --verbose

# Run specific category
python run_tests.py --unit
python run_tests.py --security
```

### Test Runner Options

Our comprehensive test runner (`run_tests.py`) provides many options:

#### By Category
```bash
python run_tests.py --unit             # Unit tests only
python run_tests.py --integration      # Integration tests only
python run_tests.py --security         # Security tests only
python run_tests.py --auth             # Auth tests only
```

#### Output Control
```bash
python run_tests.py --verbose          # Detailed output
python run_tests.py --quiet            # Minimal output
python run_tests.py --quick            # Fail fast (stop on first failure)
```

#### Coverage Reports
```bash
python run_tests.py --coverage         # Generate coverage reports
```

Coverage reports are generated in multiple formats:
- **HTML**: `htmlcov/index.html` (interactive web report)
- **Terminal**: Shows missing lines in console
- **XML**: `coverage.xml` (for CI/CD integration)

#### Specific Files or Patterns
```bash
python run_tests.py --file tests/unit/test_auth_security.py
python run_tests.py --pattern "test_password"
```

### Direct pytest Usage

You can also run tests directly with pytest:

```bash
# Basic usage
pytest tests/

# With markers
pytest -m "unit and security"
pytest -m "not integration"

# With coverage
pytest --cov=app --cov-report=html

# Verbose with specific file
pytest tests/unit/test_auth_security.py -v
```

## Test Configuration

### Central Configuration (`conftest.py`)

The `conftest.py` file provides:
- **Shared Fixtures**: Mock users, repositories, services
- **Test Markers**: Category markers for organizing tests
- **Import Path Setup**: Proper Python path configuration
- **Session Configuration**: App config for testing

### Available Fixtures

```python
# Mock data
def mock_user():
    """Returns a mock user dictionary"""

# Mock services  
def mock_user_repository():
    """Returns a mocked UserRepository"""

def mock_user_service(mock_user_repository):
    """Returns a mocked UserService"""

# Configuration
def app_config():
    """Returns test app configuration"""
```

### Test Markers

```python
pytestmark = [
    pytest.mark.unit,       # Unit test
    pytest.mark.security,   # Security test
    pytest.mark.auth,       # Auth test  
    pytest.mark.integration # Integration test
]
```

## Writing Tests

### Test Structure

```python
@pytest.mark.unit
@pytest.mark.security
class TestPasswordSecurity:
    """Test class for password security functionality."""
    
    def test_hash_password_creates_valid_hash(self):
        """Test that password hashing creates a valid hash."""
        # Arrange
        [REDACTED_PASSWORD]"
        
        # Act
        hashed = hash_password(password)
        
        # Assert
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0
```

### Test Naming Convention

- Class names: `TestFunctionalityName`
- Method names: `test_action_condition_expected_result`
- Examples:
  - `test_create_user_with_valid_data_success`
  - `test_authenticate_with_wrong_password_fails`
  - `test_hash_password_creates_valid_hash`

### Test Coverage Guidelines

For every new implementation, write:
- **At least 1 normal case test** (happy path)
- **At least 1 edge case test** (boundary conditions)
- **At least 1 failure case test** (error handling)

## Current Test Status

```
16 tests passing
Coverage: 40% overall
Key modules tested:
- core.security: 95%
- services.user_service: 97%
- db.base: 94%
```

### What's Tested

✅ **Password Security**
- Password hashing and verification
- Secure hash generation

✅ **JWT Security**  
- Token creation and validation
- Token decoding and user extraction

✅ **User Service**
- Password setting and authentication
- Google user upsert functionality

### What Needs More Testing

🔄 **Repository Layer** (29% coverage)
- Database operations
- CRUD functionality

🔄 **Main Application** (0% coverage)
- Flask routes and endpoints
- Request/response handling

🔄 **Integration Tests**
- End-to-end workflows
- Database integration

## Continuous Integration

The test runner is designed to work with CI/CD systems:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    cd backend
    python run_tests.py --coverage --quiet
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./backend/coverage.xml
```

## Troubleshooting

### Import Errors

If you see import errors, ensure:
1. You're running tests from the `backend/` directory
2. The Python path is correctly set (handled by `conftest.py`)
3. All dependencies are installed: `pip install -r requirements.txt`

### Database Issues

For integration tests that use the database:
1. Ensure PostgreSQL is running
2. Check database connection settings
3. Run migrations if needed

### Coverage Issues

If coverage reports are incomplete:
1. Make sure `pytest-cov` is installed: `pip install pytest-cov`
2. Check that test files are properly importing the modules
3. Verify the `--cov=app` parameter points to the right directory

## Best Practices

1. **Run Tests Early and Often**: Use `--quick` for fast feedback during development
2. **Use Appropriate Markers**: Tag tests properly for easy filtering
3. **Mock External Dependencies**: Keep unit tests isolated
4. **Test Edge Cases**: Don't just test the happy path
5. **Keep Tests Simple**: One concept per test method
6. **Use Descriptive Names**: Test names should explain what they verify
