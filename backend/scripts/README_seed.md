# 🌱 Seed Fake Extrato Data

Este script cria dados fictícios para testar a funcionalidade de extrato mensal.

## 📋 O que o script faz

1. **Cria usuários (artistas) fictícios:**
   - Pedro Artista (pedro.artista@teste.com)
   - Maria Artista (maria.artista@teste.com)

2. **Cria clientes fictícios:**
   - Ana Cliente
   - João Cliente  
   - Carla Cliente

3. **Cria 3 sessões para o mês anterior:**
   - Sessão 1: R$ 450,00 - Pedro Artista + Ana Cliente (Pix)
   - Sessão 2: R$ 320,00 - Maria Artista + João Cliente (Cartão)
   - Sessão 3: R$ 280,00 - Pedro Artista + Carla Cliente (Dinheiro)

4. **Cria 3 pagamentos vinculados às sessões**

5. **Cria 3 comissões com percentuais variados (30%, 25%, 35%)**

## 🚀 Como usar

### Via Docker (Recomendado)
```bash
docker-compose exec app python /app/backend/scripts/seed_fake_extrato_data.py
```

### Via Ambiente Local
```bash
# Certifique-se que o venv está ativado
python test_seed_locally.py
```

## 🧪 Testando o Extrato

Após executar o script:

1. **Gerar o extrato (opcional):**
   ```bash
   docker-compose exec app python /app/backend/scripts/generate_monthly_extrato.py --mes 8 --ano 2025 --force
   ```

2. **Acessar a página de extrato:**
   - Abra http://127.0.0.1:5000/extrato
   - Selecione mês 08 e ano 2025
   - Clique em "Buscar"
   - O modal deve aparecer com os dados fictícios

## 📊 Dados Gerados

- **Total Receita:** R$ 1.050,00
- **Total Comissões:** R$ 313,00
- **Formas de Pagamento:** Pix, Cartão, Dinheiro
- **Período:** Mês anterior (calculado automaticamente)

## 🔧 Estrutura dos Dados

```python
# Sessões
Sessao(data="2025-08-05", hora="14:00", valor=450.00, status="completed")
Sessao(data="2025-08-15", hora="16:30", valor=320.00, status="completed") 
Sessao(data="2025-08-25", hora="10:00", valor=280.00, status="completed")

# Pagamentos (vinculados às sessões)
Pagamento(data="2025-08-05", valor=450.00, forma_pagamento="Pix")
Pagamento(data="2025-08-15", valor=320.00, forma_pagamento="Cartão")
Pagamento(data="2025-08-25", valor=280.00, forma_pagamento="Dinheiro")

# Comissões (calculadas automaticamente)  
Comissao(percentual=30.00, valor=135.00)  # 30% de R$ 450
Comissao(percentual=25.00, valor=80.00)   # 25% de R$ 320
Comissao(percentual=35.00, valor=98.00)   # 35% de R$ 280
```

## ⚠️ Observações

- Os dados são criados apenas para **testes manuais**
- O script **não apaga dados existentes**, apenas adiciona novos
- Se executar múltiplas vezes, criará dados duplicados
- Para dados limpos, recriar o banco de dados

## 🎯 Objetivo

Este script foi criado especificamente para testar:
- ✅ A página de extrato (`/extrato`)
- ✅ O modal de visualização de dados
- ✅ A API `/extrato/api?mes=XX&ano=YYYY`
- ✅ O frontend JavaScript (`extrato.js`)
- ✅ A formatação de dados em tabelas
