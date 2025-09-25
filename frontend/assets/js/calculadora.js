// Initialize calculadora - check if DOM is already loaded
function initializeCalculadora() {
  const form = document.getElementById('calculadora-form');
  if (!form) return;

  const nf = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

  function showResultModal(title, content, onNewCalc = null) {
    // Use unified modal system
    openModal({
      title: title,
      body: content,
      showConfirm: !!onNewCalc,
      showCancel: true,
      confirmText: 'Novo cálculo',
      cancelText: 'Fechar',
      onConfirm: onNewCalc,
      onCancel: null,
      closeOnCancel: true,
      closeOnConfirm: true
    });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    const totalEl = document.getElementById('valor-total');
    const pctEl = document.getElementById('porcentagem');
    if (!totalEl || !pctEl) return;

    const rawTotal = totalEl.value;
    const rawPct = pctEl.value;

    // Parse numbers safely
    const total = parseFloat(String(rawTotal).replace(',', '.')) || 0;
    const pct = parseFloat(String(rawPct).replace(',', '.')) || 0;

    if (total < 0 || pct < 0) {
      showResultModal('Erro', 'Valores inválidos.');
      return;
    }

    const comissao = total * (pct / 100);
    const restante = total - comissao;

    const formattedCom = nf.format(comissao);
    const formattedTotal = nf.format(total);
    const formattedRest = nf.format(restante);

    // Define the "Novo cálculo" action
    const onNewCalc = function() {
      const formEl = document.getElementById('calculadora-form');
      if (formEl) {
        try { formEl.reset(); } catch (e) { /* ignore */ }
      }
      const first = document.getElementById('valor-total');
      if (first) first.focus();
    };

    // Inject semantic, styled content following project patterns
    const content = `
      <p><strong>Valor total:</strong> ${formattedTotal}</p>
      <p><strong>${pct}%:</strong> ${formattedCom}</p>
      <p><strong>${100 - pct}%:</strong> ${formattedRest}</p>
    `;

    // Show results with "Novo cálculo" button
    showResultModal('Resultado da Comissão', content, onNewCalc);
  });
}

// Set up initialization immediately if DOM is ready, otherwise wait for DOMContentLoaded
if (document.readyState === 'loading' || document.readyState === 'interactive') {
  document.addEventListener('DOMContentLoaded', initializeCalculadora);
} else {
  initializeCalculadora();
}
