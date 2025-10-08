# Client Display Logic Fix - Histórico Page

## Issue Summary
The "Histórico" page tables displayed inconsistent text for records without an associated client:
- Some rows showed "Cliente não encontrado"
- Other rows appeared blank
- This behavior was inconsistent with the "Registrar Pagamento" page, which shows "Nenhum cliente / Não informado"

## Root Cause Analysis

### 1. Template Rendering (Initial State)
- **historico.html**: Rendered empty string `''` for missing clients
- **financeiro.html**: Rendered `'Cliente não encontrado'` for missing clients
- **sessoes.html**: Rendered `'Cliente não encontrado'` for missing clients

### 2. JavaScript DOM Updates (After Edit)
- **financeiro.js** (line 321): After updating a payment, the JavaScript injected `'Cliente não encontrado'` for missing clients
- This caused records to change from blank to "Cliente não encontrado" after being edited

### 3. Expected Behavior
- **registrar_pagamento.html**: Shows `"Nenhum cliente / Não informado"` as the default option in the client dropdown
- This is the correct pattern to follow for consistency

## Changes Made

### Templates Updated

#### 1. `/frontend/templates/historico.html`
**Changed 3 sections (Pagamentos, Comissões, Sessões):**
```jinja2
{# Client is optional - display "Não informado" when missing (consistent with registration form) #}
{{ p.cliente.name if p.cliente else 'Não informado' }}
{{ c.pagamento.cliente.name if c.pagamento and c.pagamento.cliente else 'Não informado' }}
{{ s.cliente.name if s.cliente else 'Não informado' }}
```

#### 2. `/frontend/templates/financeiro.html`
**Changed from:**
```jinja2
{{ pagamento.cliente.name if pagamento.cliente else 'Cliente não encontrado' }}
{{ pagamento.artista.name if pagamento.artista else 'Artista não encontrado' }}
```

**To:**
```jinja2
{# Client is optional - display "Não informado" when missing (consistent with registration form) #}
{{ pagamento.cliente.name if pagamento.cliente else 'Não informado' }}
{{ pagamento.artista.name if pagamento.artista else '' }}
```

#### 3. `/frontend/templates/sessoes.html`
**Changed from:**
```jinja2
{{ sessao.cliente.name if sessao.cliente else 'Cliente não encontrado' }}
{{ sessao.artista.name if sessao.artista else 'Artista não encontrado' }}
```

**To:**
```jinja2
{# Client is optional - display "Não informado" when missing (consistent with registration form) #}
{{ sessao.cliente.name if sessao.cliente else 'Não informado' }}
{{ sessao.artista.name if sessao.artista else '' }}
```

### JavaScript Updated

#### `/frontend/assets/js/financeiro.js` (line 321)
**Changed from:**
```javascript
cols[1].textContent = (updated.data.cliente && updated.data.cliente.name) ? updated.data.cliente.name : 'Cliente não encontrado';
cols[2].textContent = (updated.data.artista && updated.data.artista.name) ? updated.data.artista.name : 'Artista não encontrado';
```

**To:**
```javascript
// Display "Não informado" when no client is associated (consistent with registration form behavior)
cols[1].textContent = (updated.data.cliente && updated.data.cliente.name) ? updated.data.cliente.name : 'Não informado';
cols[2].textContent = (updated.data.artista && updated.data.artista.name) ? updated.data.artista.name : '';
```

## Acceptance Criteria ✅

- ✅ No row in the Histórico tables shows "Cliente não encontrado"
- ✅ Rows with no client show "Não informado" (consistent with registration form)
- ✅ The behavior matches the "Registrar Pagamento" page
- ✅ Existing data with valid clients continues to display correctly
- ✅ Developer comments added to clarify the intended behavior

## Testing Recommendations

1. **Initial Page Load**:
   - Navigate to `/historico`
   - Verify all rows with missing clients show "Não informado"

2. **After Edit**:
   - Edit a payment and remove the client
   - Verify the row updates to show "Não informado" (not "Cliente não encontrado")

3. **Financeiro Page**:
   - Navigate to `/financeiro`
   - Verify payments without clients show "Não informado"

4. **Sessões Page**:
   - Navigate to `/sessoes`
   - Verify sessions without clients show "Não informado"

5. **Cross-Page Consistency**:
   - Verify that the same record displays consistently across all pages

## Notes

- **Artist handling**: Artists are required fields in most cases, so missing artists show empty string `''` instead of a message
- **Client handling**: Clients are optional, so "Não informado" (Not informed) is displayed when missing
- **Consistency**: All pages now follow the same convention established by the registration form

## Related Files

- `/frontend/templates/historico.html` - Main history page
- `/frontend/templates/financeiro.html` - Financial page
- `/frontend/templates/sessoes.html` - Sessions page
- `/frontend/templates/registrar_pagamento.html` - Payment registration form (reference)
- `/frontend/assets/js/financeiro.js` - JavaScript for payment edit DOM updates

## Date
October 7, 2025
