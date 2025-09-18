function toggleOptions(btn) {
    var actions = btn.parentElement.querySelector('.options-actions');
    if (actions) {
        actions.classList.toggle('visible');
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