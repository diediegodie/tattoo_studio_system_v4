// modal.js - Unified Modal Component
// Provides openModal() and closeModal() functions with accessibility and focus management

let modalInstance = null;
let modalCallbacks = {};
let previousFocusElement = null;

// Initialize modal on page load
document.addEventListener('DOMContentLoaded', function() {
    // Create modal instance from template
    const modalTemplate = `
        <div id="unified-modal" class="modal-overlay modal-hidden" role="dialog" aria-modal="true" aria-labelledby="modal-title">
            <div class="modal-container" tabindex="-1">
                <div class="modal-scrollable">
                    <h2 id="modal-title"></h2>
                    <div id="modal-body" aria-live="polite"></div>
                </div>
                <div class="modal-footer">
                    <button type="button" id="modal-cancel-btn" class="button">Cancelar</button>
                    <button type="button" id="modal-confirm-btn" class="button primary">Confirmar</button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalTemplate);
    modalInstance = document.getElementById('unified-modal');

    // Set up event listeners
    setupModalEventListeners();
});

/**
 * Open modal with specified content and callbacks
 * @param {Object} options - Modal configuration
 * @param {string} options.title - Modal title
 * @param {string} options.body - Modal body content (HTML allowed)
 * @param {Function} options.onConfirm - Callback for confirm button
 * @param {Function} options.onCancel - Callback for cancel button
 * @param {string} options.confirmText - Text for confirm button (default: "Confirmar")
 * @param {string} options.cancelText - Text for cancel button (default: "Cancelar")
 * @param {boolean} options.showCancel - Whether to show cancel button (default: true)
 * @param {boolean} options.showConfirm - Whether to show confirm button (default: true)
 * @param {Array} options.customButtons - Array of custom button configurations
 * @param {boolean} options.closeOnConfirm - Whether to close modal on confirm (default: true)
 * @param {boolean} options.closeOnCancel - Whether to close modal on cancel (default: true)
 */
function openModal(options = {}) {
    if (!modalInstance) {
        console.error('Modal not initialized');
        return;
    }

    const {
        title = '',
        body = '',
        onConfirm = null,
        onCancel = null,
        confirmText = 'Confirmar',
        cancelText = 'Cancelar',
        showCancel = true,
        showConfirm = true,
        customButtons = [],
        closeOnConfirm = true,
        closeOnCancel = true
    } = options;

    // Store callbacks and options
    modalCallbacks = { 
        onConfirm, 
        onCancel, 
        closeOnConfirm, 
        closeOnCancel,
        customButtons 
    };

    // Update modal content
    const titleElement = modalInstance.querySelector('#modal-title');
    const bodyElement = modalInstance.querySelector('#modal-body');
    const footerElement = modalInstance.querySelector('.modal-footer');

    if (titleElement) titleElement.textContent = title;
    if (bodyElement) bodyElement.innerHTML = body;

    // Clear existing buttons
    const existingButtons = footerElement.querySelectorAll('button:not(#modal-cancel-btn):not(#modal-confirm-btn)');
    existingButtons.forEach(btn => btn.remove());

    // Handle default buttons
    const cancelBtn = modalInstance.querySelector('#modal-cancel-btn');
    const confirmBtn = modalInstance.querySelector('#modal-confirm-btn');

    if (cancelBtn) {
        cancelBtn.textContent = cancelText;
        cancelBtn.classList.toggle('modal-btn-visible', showCancel);
        cancelBtn.classList.toggle('modal-btn-hidden', !showCancel);
    }
    if (confirmBtn) {
        confirmBtn.textContent = confirmText;
        confirmBtn.classList.toggle('modal-btn-visible', showConfirm);
        confirmBtn.classList.toggle('modal-btn-hidden', !showConfirm);
    }

    // Add custom buttons
    customButtons.forEach((buttonConfig, index) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = buttonConfig.class || 'button';
        button.textContent = buttonConfig.text;
        button.id = `custom-btn-${index}`;
        
        button.addEventListener('click', function() {
            if (buttonConfig.action) {
                buttonConfig.action();
            }
            if (buttonConfig.closeModal !== false) {
                closeModal();
            }
        });

            // Insert before default buttons
            if (confirmBtn && confirmBtn.classList.contains('modal-btn-visible')) {
                footerElement.insertBefore(button, confirmBtn);
            } else if (cancelBtn && cancelBtn.classList.contains('modal-btn-visible')) {
                footerElement.insertBefore(button, cancelBtn);
            } else {
                footerElement.appendChild(button);
            }
        });

    // Store previous focus element
    previousFocusElement = document.activeElement;

    // Show modal using CSS classes only
    modalInstance.classList.remove('modal-hidden');
    modalInstance.classList.add('modal-visible');    // Set up focus trap for this modal instance
    setupFocusTrap();

    // Focus management
    const container = modalInstance.querySelector('.modal-container');
    if (container) {
        container.focus();
    }

    // Prevent body scroll
    document.body.classList.add('modal-open');
}

/**
 * Close the modal
 */
function closeModal() {
    if (!modalInstance) return;

    // Reset to default CSS classes
    const overlayElement = modalInstance;
    const containerElement = modalInstance.querySelector('.modal-container') || modalInstance.querySelector('.cadastro-modal-content');
    
    if (overlayElement) {
        overlayElement.className = 'modal-overlay';
    }
    if (containerElement) {
        containerElement.className = 'modal-container';
    }

    // Hide modal using CSS classes only
    modalInstance.classList.remove('modal-visible');
    modalInstance.classList.add('modal-hidden');

    // Restore body scroll
    document.body.classList.remove('modal-open');

    // Restore focus
    if (previousFocusElement && typeof previousFocusElement.focus === 'function') {
        previousFocusElement.focus();
    }

    // Clear callbacks
    modalCallbacks = {};
}

/**
 * Set up modal event listeners for accessibility and interaction
 */
function setupModalEventListeners() {
    if (!modalInstance) return;

    const overlay = modalInstance;
    const cancelBtn = modalInstance.querySelector('#modal-cancel-btn');
    const confirmBtn = modalInstance.querySelector('#modal-confirm-btn');

    // Click outside to close
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) {
            handleCancel();
        }
    });

    // ESC key to close
    document.addEventListener('keydown', function(e) {
    if (modalInstance.classList.contains('modal-visible') && e.key === 'Escape') {
            handleCancel();
        }
    });

    // Button click handlers - use event delegation to handle dynamic class changes
    if (cancelBtn) {
        cancelBtn.addEventListener('click', handleCancel);
    }

    if (confirmBtn) {
        confirmBtn.addEventListener('click', handleConfirm);
    }

    // Focus trap - will be set up dynamically when modal opens
}

/**
 * Set up focus trap for the current modal instance
 */
function setupFocusTrap() {
    if (!modalInstance) return;

    const container = modalInstance.querySelector('.modal-container') ||
                     modalInstance.querySelector('.cadastro-modal-content') ||
                     modalInstance.querySelector('[class*="modal-content"]');

    if (container) {
        container.addEventListener('keydown', function(e) {
            if (e.key === 'Tab') {
                // Get all focusable elements including those in custom content
                const focusableElements = container.querySelectorAll(
                    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                );
                const firstElement = focusableElements[0];
                const lastElement = focusableElements[focusableElements.length - 1];

                if (e.shiftKey) {
                    if (document.activeElement === firstElement) {
                        lastElement.focus();
                        e.preventDefault();
                    }
                } else {
                    if (document.activeElement === lastElement) {
                        firstElement.focus();
                        e.preventDefault();
                    }
                }
            }
        });
    }
}

/**
 * Handle cancel action
 */
function handleCancel() {
    if (modalCallbacks.onCancel) {
        modalCallbacks.onCancel();
    }
    if (modalCallbacks.closeOnCancel !== false) {
        closeModal();
    }
}

/**
 * Handle confirm action
 */
function handleConfirm() {
    console.log('[DEBUG] handleConfirm called - modal confirm button clicked');
    console.log('[DEBUG] Current modalCallbacks:', modalCallbacks);

    // If onConfirm callback is provided, use it
    if (modalCallbacks.onConfirm) {
        console.log('[DEBUG] Executing onConfirm callback');
        try {
            const result = modalCallbacks.onConfirm();
            console.log('[DEBUG] onConfirm callback executed, result:', result);
            if (modalCallbacks.closeOnConfirm !== false) {
                console.log('[DEBUG] Closing modal after onConfirm');
                closeModal();
            } else {
                console.log('[DEBUG] Not closing modal (closeOnConfirm is false)');
            }
        } catch (error) {
            console.error('[DEBUG] Error in onConfirm callback:', error);
        }
        return;
    }

    // If no onConfirm callback, check if there's a form in the modal and submit it
    const modalBody = modalInstance.querySelector('#modal-body');
    if (modalBody) {
        const form = modalBody.querySelector('form');
        if (form) {
            console.log('[DEBUG] Found form in modal, dispatching submit event');
            // Create a submit event to trigger form validation and onsubmit handlers
            const submitEvent = new Event('submit', { cancelable: true });
            const submitSuccessful = form.dispatchEvent(submitEvent);

            console.log('[DEBUG] Form submit event dispatched, successful:', submitSuccessful);

            // Only close modal if form submission was not prevented
            if (submitSuccessful && modalCallbacks.closeOnConfirm !== false) {
                console.log('[DEBUG] Closing modal after form submission');
                closeModal();
            } else {
                console.log('[DEBUG] Not closing modal after form submission');
            }
            return;
        } else {
            console.log('[DEBUG] No form found in modal body');
        }
    } else {
        console.log('[DEBUG] No modal body found');
    }

    console.log('[DEBUG] No onConfirm callback and no form found, closing modal');
    if (modalCallbacks.closeOnConfirm !== false) {
        closeModal();
    }
    // If no callback and no form, just close the modal
    if (modalCallbacks.closeOnConfirm !== false) {
        closeModal();
    }
}

/**
 * Open modal with custom content and callbacks (for complex forms)
 * @param {Object} options - Modal configuration
 * @param {string} options.title - Modal title
 * @param {string} options.content - Custom HTML content (can include forms, etc.)
 * @param {Function} options.onConfirm - Callback for confirm button
 * @param {Function} options.onCancel - Callback for cancel button
 * @param {string} options.confirmText - Text for confirm button (default: "Confirmar")
 * @param {string} options.cancelText - Text for cancel button (default: "Cancelar")
 * @param {boolean} options.showCancel - Whether to show cancel button (default: true)
 * @param {boolean} options.showConfirm - Whether to show confirm button (default: true)
 * @param {Array} options.customButtons - Array of custom button configurations
 * @param {boolean} options.closeOnConfirm - Whether to close modal on confirm (default: true)
 * @param {boolean} options.closeOnCancel - Whether to close modal on cancel (default: true)
 * @param {string} options.overlayClass - Custom CSS class for overlay (default: "modal-overlay")
 * @param {string} options.containerClass - Custom CSS class for container (default: "modal-container")
 */
function openCustomModal(options = {}) {
    console.log('[MODAL] openCustomModal called with options:', options);
    
    if (!modalInstance) {
        console.error('[MODAL] Modal not initialized - modalInstance is null!');
        return;
    }
    
    console.log('[MODAL] modalInstance exists:', modalInstance);

    const {
        title = '',
        content = '',
        onConfirm = null,
        onCancel = null,
        confirmText = 'Confirmar',
        cancelText = 'Cancelar',
        showCancel = true,
        showConfirm = true,
        customButtons = [],
        closeOnConfirm = true,
        closeOnCancel = true,
        overlayClass = 'modal-overlay',
        containerClass = 'modal-container'
    } = options;
    
    console.log('[MODAL] Parsed options - title:', title, 'showConfirm:', showConfirm, 'showCancel:', showCancel);

    // Store callbacks and options
    modalCallbacks = { 
        onConfirm, 
        onCancel, 
        closeOnConfirm, 
        closeOnCancel,
        customButtons,
        useCustomContent: true 
    };

    // Update modal classes if custom
    const overlayElement = modalInstance;
    const containerElement = modalInstance.querySelector('.modal-container');
    
    if (overlayElement) {
        overlayElement.className = overlayClass;
    }
    if (containerElement) {
        containerElement.className = containerClass + ' modal-scrollable-container';
    }

    // Update modal content
    const scrollableElement = modalInstance.querySelector('.modal-scrollable') || modalInstance.querySelector('.modal-container');
    if (scrollableElement && content) {
        // If using custom container class, we need to structure differently
        if (containerClass !== 'modal-container') {
            scrollableElement.innerHTML = `<h2 id="modal-title">${title}</h2>${content}`;
        } else {
            const scrollableDiv = modalInstance.querySelector('.modal-scrollable');
            if (scrollableDiv) {
                scrollableDiv.innerHTML = `<h2 id="modal-title">${title}</h2>${content}`;
            }
        }
    }

    // Handle footer
    let footerElement = modalInstance.querySelector('.modal-footer');
    if (!footerElement && containerClass === 'modal-container') {
        // Create footer if it doesn't exist
        const container = modalInstance.querySelector('.modal-container');
        if (container) {
            footerElement = document.createElement('div');
            footerElement.className = 'modal-footer';
            container.appendChild(footerElement);
        }
    }

    // Clear existing custom buttons
    if (footerElement) {
        const existingButtons = footerElement.querySelectorAll('button:not(#modal-cancel-btn):not(#modal-confirm-btn)');
        existingButtons.forEach(btn => btn.remove());
    }

    // Handle default buttons
    const cancelBtn = modalInstance.querySelector('#modal-cancel-btn');
    const confirmBtn = modalInstance.querySelector('#modal-confirm-btn');

    if (cancelBtn) {
        cancelBtn.textContent = cancelText;
        cancelBtn.classList.toggle('modal-btn-visible', showCancel);
        cancelBtn.classList.toggle('modal-btn-hidden', !showCancel);
    }
    if (confirmBtn) {
        confirmBtn.textContent = confirmText;
        confirmBtn.classList.toggle('modal-btn-visible', showConfirm);
        confirmBtn.classList.toggle('modal-btn-hidden', !showConfirm);
    }

    // Add custom buttons
    if (footerElement) {
        customButtons.forEach((buttonConfig, index) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = buttonConfig.class || 'button';
            button.textContent = buttonConfig.text;
            button.id = `custom-btn-${index}`;
            
            button.addEventListener('click', function() {
                if (buttonConfig.action) {
                    buttonConfig.action();
                }
                if (buttonConfig.closeModal !== false) {
                    closeModal();
                }
            });

            // Insert before default buttons
            if (confirmBtn && confirmBtn.classList.contains('modal-btn-visible')) {
                footerElement.insertBefore(button, confirmBtn);
            } else if (cancelBtn && cancelBtn.classList.contains('modal-btn-visible')) {
                footerElement.insertBefore(button, cancelBtn);
            } else {
                footerElement.appendChild(button);
            }
        });
    }

    // Store previous focus element
    previousFocusElement = document.activeElement;

    console.log('[MODAL] About to show modal, classes before:', modalInstance.className);
    
    // Show modal using CSS classes only
    modalInstance.classList.remove('modal-hidden');
    modalInstance.classList.add('modal-visible');
    
    console.log('[MODAL] Modal should now be visible, classes after:', modalInstance.className);

    // Set up focus trap for this modal instance
    setupFocusTrap();

    // Focus management
    const container = modalInstance.querySelector('.modal-container') || modalInstance.querySelector(`.${containerClass}`);
    if (container) {
        container.focus();
    }

    // Prevent body scroll
    document.body.classList.add('modal-open');
    
    console.log('[MODAL] openCustomModal completed successfully');
}

// Export functions for global use
window.openModal = openModal;
window.openCustomModal = openCustomModal;
window.closeModal = closeModal;