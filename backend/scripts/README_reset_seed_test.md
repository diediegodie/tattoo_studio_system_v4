# Reset, Seed & Test Script

This script provides a complete workflow for resetting the Tattoo Studio Management System database, seeding it with test data, and running automated tests.

## Usage

### Standalone Script
```bash
cd backend
python scripts/reset_seed_test.py [options]
```

### Options
- `--skip-reset`: Skip database reset
- `--skip-seed`: Skip data seeding
- `--skip-tests`: Skip test execution
- `--help`: Show help message

### Environment Variables
- `HISTORICO_DEBUG=1`: Enable debug logging for historico endpoint
- `DOCKER_RESET=1`: Force Docker reset mode
- `FORCE_DOCKER_DB=1`: Force use of Docker database even in local mode

## What It Does

### 1. Database Reset
- **Docker**: `docker-compose down -v` then `docker-compose up -d db`
- **Local**: Creates/resets local SQLite database at `tattoo_studio_dev.db`

### 2. Seed Test Data
Creates current month test data:
- 1 Cliente, 1 Artista
- 1 Pagamento (R$ 500.00)
- 1 Sessão (R$ 800.00)
- 2 Comissões (R$ 350.00 + R$ 560.00)
- 1 Gasto (R$ 455.00)

Expected totals: Receita R$ 1300.00, Comissões R$ 910.00, Despesas R$ 455.00, Líquida R$ 390.00

### 3. Run Tests
Executes pytest on `test_historico.py` and related tests. Fails if any test fails.

### 4. Console Output
Provides clear step-by-step status with emojis and detailed information.

## Examples

```bash
# Full reset, seed, and test
python scripts/reset_seed_test.py

# Skip database reset (useful for quick re-testing)
python scripts/reset_seed_test.py --skip-reset

# Only seed data without running tests
python scripts/reset_seed_test.py --skip-tests

# Only run tests without resetting/seeding
python scripts/reset_seed_test.py --skip-reset --skip-seed
```

## Output Example

```
🎨 Tattoo Studio System - Reset, Seed & Test
==================================================
🔍 Environment detected: local
🔄 Resetting database...
  💻 Using local SQLite database...
  ✅ Database reset complete (Local SQLite: /path/to/tattoo_studio_dev.db)
🌱 Seeding test data...
  ✅ Test data seeded:
    - 1 Cliente, 1 Artista
    - 1 Pagamento (R$ 500.00)
    - 1 Sessão (R$ 800.00)
    - 2 Comissões (R$ 350.00 + R$ 560.00)
    - 1 Gasto (R$ 455.00)
    - Expected totals: Receita R$ 1300.00, Comissões R$ 910.00, Despesas R$ 455.00, Líquida R$ 390.00
🔄 Seeding edge case data...
  ✅ Edge cases handled in test suite
🧪 Running automated tests...
  ✅ All tests passed!
  [test output...]
==================================================
🎉 All operations completed successfully!
📊 System ready for manual validation:
   - Visit /historico for current month totals
   - Visit /extrato for historical data
```