// Initialize calculadora - check if DOM is already loaded
function initializeCalculadora() {
  console.log('[calculadora] Initializing calculator...');
  
  const form = document.getElementById('calculadora-form');
  if (!form) {
    console.error('[calculadora] Form with id "calculadora-form" not found');
    return;
  }

  console.log('[calculadora] Form found, attaching event listener');

  const nf = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

  function showResultModal(title, content, onNewCalc = null) {
    // Use unified modal system if available
    if (typeof window.openModal === 'function') {
      console.log('[calculadora] Opening modal with results');
      window.openModal({
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
    } else {
      console.warn('[calculadora] openModal function not available, modal will not be shown');
    }
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    console.log('[calculadora] Form submitted, preventing default');

    const totalEl = document.getElementById('valor-total');
    const pctEl = document.getElementById('porcentagem');
    
    if (!totalEl || !pctEl) {
      console.error('[calculadora] Input elements not found');
      return;
    }

    const rawTotal = totalEl.value;
    const rawPct = pctEl.value;

    console.log('[calculadora] Input values:', { rawTotal, rawPct });

    // Parse numbers safely
    const total = parseFloat(String(rawTotal).replace(',', '.')) || 0;
    const pct = parseFloat(String(rawPct).replace(',', '.')) || 0;

    console.log('[calculadora] Parsed values:', { total, pct });

    if (total < 0 || pct < 0) {
      console.warn('[calculadora] Invalid values detected');
      showResultModal('Erro', 'Valores inválidos.');
      return;
    }

    const comissao = total * (pct / 100);
    const restante = total - comissao;

    const formattedCom = nf.format(comissao);
    const formattedTotal = nf.format(total);
    const formattedRest = nf.format(restante);

    console.log('[calculadora] Calculation results:', { comissao, restante });

    // Define the "Novo cálculo" action
    const onNewCalc = function() {
      console.log('[calculadora] Resetting form for new calculation');
      const formEl = document.getElementById('calculadora-form');
      if (formEl) {
        try { formEl.reset(); } catch (e) { console.error('[calculadora] Error resetting form:', e); }
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
      console.log('[calculadora] Displaying results in result block');
      resultadoBlock.innerHTML = `<h2>Resultado da Comissão</h2>${content}<button id='novo-calculo-btn' class='button primary'>Novo cálculo</button>`;
      resultadoBlock.style.display = 'block';
      resultadoBlock.classList.remove('hidden');
      
      // Scroll to result
      resultadoBlock.scrollIntoView({ behavior: 'smooth', block: 'center' });
      
      // Novo cálculo button resets form and hides result
      var novoCalcBtn = document.getElementById('novo-calculo-btn');
      if (novoCalcBtn) {
        novoCalcBtn.addEventListener('click', function() {
          console.log('[calculadora] New calculation button clicked');
          form.reset();
          resultadoBlock.style.display = 'none';
          resultadoBlock.classList.add('hidden');
          document.getElementById('valor-total').focus();
        });
      }
    } else {
      console.error('[calculadora] Result block with id "calc-resultado" not found');
    }
    
    // Optionally, close modal if it's open
    if (typeof window.closeModal === 'function') {
      try { 
        window.closeModal(); 
      } catch(e) {
        console.warn('[calculadora] Error closing modal:', e);
      }
    }

  });
  
  console.log('[calculadora] Event listener attached successfully');
}

// Set up initialization immediately if DOM is ready, otherwise wait for DOMContentLoaded
if (document.readyState === 'loading' || document.readyState === 'interactive') {
  console.log('[calculadora] DOM still loading, waiting for DOMContentLoaded event');
  document.addEventListener('DOMContentLoaded', initializeCalculadora);
} else {
  console.log('[calculadora] DOM already loaded, initializing immediately');
  initializeCalculadora();
}
