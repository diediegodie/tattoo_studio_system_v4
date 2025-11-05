// agenda.js - Agenda page functionality

function toggleDetails(detailsId) {
    const detailsElement = document.getElementById(detailsId);
    if (detailsElement) {
        detailsElement.classList.toggle('hidden');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Event delegation for create session button
    document.addEventListener('click', function(e) {
        // Handle create session button clicks to stop propagation
        if (e.target.closest('.create-session-btn')) {
            e.stopPropagation();
            return;
        }

        // Row toggle is handled by common.js
    });
});