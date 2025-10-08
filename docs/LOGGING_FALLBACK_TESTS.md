# Logging Fallback Tests

## Overview

This test suite (`test_logging_fallback.py`) validates that the Flask application's logging system gracefully handles disk write failures by automatically falling back to stdout/console output without crashing the application.

## Purpose

In production environments, various disk-related failures can occur:
- **Disk full**: No space left on device
- **Read-only filesystem**: Directory permissions changed
- **I/O errors**: Hardware failures, network filesystem issues
- **Permission errors**: Incorrect file/directory permissions

The logging system must continue to function even when file handlers fail, ensuring that:
1. The application doesn't crash due to logging errors
2. Log messages are still captured (via console/stdout fallback)
3. Operations continue normally despite logging configuration failures

## Test Coverage

### TestLoggingFallbackOnDiskFailure

#### 1. `test_logging_fallback_on_file_handler_failure`
- **Purpose**: Verify that when RotatingFileHandler initialization fails, logging falls back to stdout
- **Method**: Mocks RotatingFileHandler to raise IOError
- **Assertions**:
  - No exception is raised during setup
  - Log messages appear in stdout
  - Application continues to run

#### 2. `test_logging_continues_after_file_write_failure`
- **Purpose**: Ensure subsequent log messages work after initial failure
- **Method**: Simulates "No space left on device" error
- **Assertions**:
  - Multiple log messages (INFO, WARNING, ERROR) all appear in stdout
  - Logging remains functional throughout application lifecycle

#### 3. `test_logging_with_read_only_directory`
- **Purpose**: Test behavior when logs directory exists but is read-only
- **Method**: Creates read-only directory, mocks PermissionError
- **Assertions**:
  - Setup completes without crashing
  - DEBUG and INFO messages appear in console output

#### 4. `test_error_handler_fallback`
- **Purpose**: Verify that both file handlers (app.log and errors.log) can fail independently
- **Method**: Both RotatingFileHandler calls raise IOError
- **Assertions**:
  - Errors with tracebacks still appear in stdout
  - Exception info is properly formatted

#### 5. `test_console_handler_always_present`
- **Purpose**: Confirm console handler is always configured regardless of file handler status
- **Method**: Simulates catastrophic disk failure
- **Assertions**:
  - At least one StreamHandler exists in root logger
  - Console handler successfully logs messages

#### 6. `test_logging_with_json_format_fallback`
- **Purpose**: Verify JSON formatting works with fallback handler
- **Method**: File handler fails, JSON format enabled
- **Assertions**:
  - JSON-formatted messages appear in stdout
  - Extra context (user_id) is included in output

#### 7. `test_multiple_loggers_after_disk_failure`
- **Purpose**: Ensure multiple named loggers work after disk failure
- **Method**: Creates loggers for different modules
- **Assertions**:
  - All loggers (module1, module2, app.service) produce output
  - Messages from all loggers appear in stdout

#### 8. `test_no_exception_propagation_on_handler_error`
- **Purpose**: Verify that handler setup exceptions don't propagate to caller
- **Method**: Raises RuntimeError during handler initialization
- **Assertions**:
  - `setup_logging()` completes without raising exception
  - Subsequent logging calls work normally

#### 9. `test_various_disk_errors_handled` (parametrized)
- **Purpose**: Test various disk-related error types
- **Parameters**: 
  - IOError ("Input/output error")
  - OSError ("No space left on device")
  - PermissionError ("Permission denied")
  - FileNotFoundError ("Directory not found")
- **Assertions**: All error types are handled gracefully

### TestLoggingIdempotency

#### 10. `test_repeated_setup_after_failure`
- **Purpose**: Verify `setup_logging()` can be called multiple times after failure
- **Method**: Calls setup_logging 3 times with disk failure simulated
- **Assertions**:
  - All 3 setups complete successfully
  - Messages from all iterations appear in stdout

#### 11. `test_handler_cleanup_before_setup`
- **Purpose**: Ensure existing handlers are properly cleaned up before adding new ones
- **Method**: Calls setup_logging multiple times, counts handlers
- **Assertions**:
  - Handler count remains consistent across multiple setups
  - No handler leaks or duplicates

## Implementation Details

### Fallback Mechanism

The `setup_logging()` function in `app/core/logging_config.py` implements the following fallback strategy:

```python
# Console handler is always added first
console_handler = logging.StreamHandler(sys.stdout)
root_logger.addHandler(console_handler)

# File handlers wrapped in try-except
try:
    file_handler = logging.handlers.RotatingFileHandler(...)
    root_logger.addHandler(file_handler)
except Exception as e:
    # Log warning to console, continue with console-only logging
    console_handler.handle(LogRecord(...))
```

### Key Features

1. **Console Handler Priority**: StreamHandler is added before attempting file handlers
2. **Independent Error Handling**: Each file handler (app.log, errors.log) has its own try-except
3. **Broad Exception Catching**: Catches all `Exception` types to handle unexpected errors
4. **Graceful Degradation**: Logs warning messages about failures but continues execution
5. **No Exception Propagation**: Errors don't bubble up to crash the application

## Running the Tests

### Run all logging tests:
```bash
cd backend
pytest tests/unit/test_logging_fallback.py -v
```

### Run specific test:
```bash
pytest tests/unit/test_logging_fallback.py::TestLoggingFallbackOnDiskFailure::test_logging_fallback_on_file_handler_failure -v
```

### Run with coverage:
```bash
pytest tests/unit/test_logging_fallback.py --cov=app.core.logging_config --cov-report=term-missing
```

### Run only logging-marked tests:
```bash
pytest -m logging -v
```

## Expected Output

All tests should pass with output similar to:
```
tests/unit/test_logging_fallback.py::TestLoggingFallbackOnDiskFailure::test_logging_fallback_on_file_handler_failure PASSED
tests/unit/test_logging_fallback.py::TestLoggingFallbackOnDiskFailure::test_logging_continues_after_file_write_failure PASSED
...
======================== 14 passed in 0.11s ========================
```

## Integration with CI/CD

These tests should be included in:
- **Pre-commit hooks**: Run before allowing commits
- **CI pipeline**: Run on every pull request
- **Deployment checks**: Validate before production deployment

## Troubleshooting

### Test Failures

If tests fail, check:
1. **Logging configuration**: Verify `logging_config.py` has try-except blocks
2. **Handler cleanup**: Ensure fixtures properly clean up logging state
3. **Mock configuration**: Verify mocks are properly scoped to test functions

### Common Issues

- **Handler leaks**: Use `clean_logging` fixture to reset logging state
- **Capsys timing**: Ensure `capsys.readouterr()` is called after logging operations
- **Mock side effects**: Verify mock.side_effect is set correctly for exceptions

## Acceptance Criteria ✅

All requirements met:

✅ **Simulate disk failure**: Multiple methods (IOError, OSError, PermissionError, read-only dirs)  
✅ **Fallback behavior**: Automatic redirection to stdout via console handler  
✅ **No crashes**: Application continues running without unhandled exceptions  
✅ **Test cases**: 14 comprehensive tests covering all scenarios  
✅ **Implementation**: Error handling in `setup_logging()` with broad exception catching  
✅ **pytest compatible**: Uses capsys for output capture, mocking for failure simulation  
✅ **Idempotent**: Fallback behavior works consistently across multiple calls  
✅ **All tests pass**: 14/14 tests passing ✅

## Related Files

- **Tests**: `backend/tests/unit/test_logging_fallback.py`
- **Implementation**: `backend/app/core/logging_config.py`
- **Configuration**: `backend/pytest.ini` (logging marker)
- **Documentation**: `docs/LOGGING_FALLBACK_TESTS.md` (this file)
