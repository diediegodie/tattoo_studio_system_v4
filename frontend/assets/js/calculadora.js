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

    // Show results in centered block
    var resultadoBlock = document.getElementById('calc-resultado');
    if (resultadoBlock) {
      resultadoBlock.innerHTML = `<h2>Resultado da Comissão</h2>${content}<button id='novo-calculo-btn' class='button primary'>Novo cálculo</button>`;
      resultadoBlock.style.display = '';
      // Scroll to result
      resultadoBlock.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // Novo cálculo button resets form and hides result
      var novoCalcBtn = document.getElementById('novo-calculo-btn');
      if (novoCalcBtn) {
        novoCalcBtn.addEventListener('click', function() {
          form.reset();
          resultadoBlock.style.display = 'none';
          document.getElementById('valor-total').focus();
        });
      }
    }
    // Optionally, hide modal if open
    if (typeof closeModal === 'function') try { closeModal(); } catch(e) {}

  });
}

// Set up initialization immediately if DOM is ready, otherwise wait for DOMContentLoaded
if (document.readyState === 'loading' || document.readyState === 'interactive') {
  document.addEventListener('DOMContentLoaded', initializeCalculadora);
} else {
  initializeCalculadora();
}
