function toggleOptions(btn) {
    console.log('[DEBUG] toggleOptions called with button:', btn);
    var actions = btn.parentElement.querySelector('.options-actions');
    console.log('[DEBUG] Found actions element in parent:', actions);

    // If not found in parent, try to find in siblings
    if (!actions) {
        var siblings = btn.parentElement.children;
        for (var i = 0; i < siblings.length; i++) {
            if (siblings[i].classList && siblings[i].classList.contains('options-actions')) {
                actions = siblings[i];
                console.log('[DEBUG] Found actions element in siblings:', actions);
                break;
            }
        }
    }

    if (actions) {
        var wasVisible = actions.classList.contains('visible');
        actions.classList.toggle('visible');
        var isVisible = actions.classList.contains('visible');
        console.log('[DEBUG] Toggled visibility from', wasVisible, 'to', isVisible);
    } else {
        console.warn('[DEBUG] No .options-actions element found for button:', btn);
    }
}

function toggleDetails(id) {
    var row = document.getElementById(id);
    if (row) {
        row.classList.toggle('visible');
    }
}

// Add event listeners for options buttons
function setupCommonEventListeners() {
    // Remove potentially conflicting event delegation
    // The inline onclick handlers should work without interference
    console.log('Common event listeners setup complete');
}

// Set up event listeners when DOM is ready
function initializeCommon() {
    setupCommonEventListeners();
}

// Expose functions to global scope for HTML onclick handlers
window.toggleOptions = toggleOptions;
window.toggleDetails = toggleDetails;

// Centralized notification helpers
window.notifySuccess = function(message) {
  if (window.showToast) {
    window.showToast(message, 'success');
  } else {
    console.log('SUCCESS:', message);
  }
};

window.notifyError = function(message) {
  if (window.showToast) {
    window.showToast(message, 'error');
  } else {
    console.error('ERROR:', message);
  }
};

window.notifyWarning = function(message) {
  if (window.showToast) {
    window.showToast(message, 'info'); // Using 'info' since CSS has success/error/info
  } else {
    console.warn('WARNING:', message);
  }
};

// Centralized confirmation dialog helper
window.confirmAction = function(message, title = 'Confirmar exclusão') {
  console.log('[DEBUG] confirmAction called with message:', message);
  return new Promise((resolve) => {
    // Use unified modal system
    openModal({
      title: title,
      body: `<p>${message}</p>`,
      confirmText: 'Confirmar',
      cancelText: 'Cancelar',
        // Keep the modal open on confirm so callers can perform async deletion and then close it
        onConfirm: () => {
          console.log('[DEBUG] confirmAction onConfirm executed - user confirmed (modal will remain open)');
          resolve(true);
        },
        closeOnConfirm: false,
      onCancel: () => {
        console.log('[DEBUG] confirmAction onCancel executed - user cancelled');
        resolve(false);
      }
    });
  });
};

// Development utility for simulating API responses
// Only active in development mode
window.simulateApiResult = function(success = true, delay = 1000, customMessage = null) {
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    console.warn('simulateApiResult is only available in development');
    return;
  }
  
  return new Promise((resolve) => {
    setTimeout(() => {
      if (success) {
        resolve({
          success: true,
          message: customMessage || 'Ação concluída com sucesso.',
          data: {}
        });
      } else {
        resolve({
          success: false,
          message: customMessage || 'Não foi possível concluir a ação. Tente novamente.'
        });
      }
    }, delay);
  });
};