// agenda.js - Agenda page functionality

function toggleDetails(detailsId) {
    const detailsElement = document.getElementById(detailsId);
    if (detailsElement) {
        detailsElement.classList.toggle('hidden');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Event delegation for client rows and buttons
    document.addEventListener('click', function(e) {
        // Handle client row clicks
        const clientRow = e.target.closest('.client-row');
        if (clientRow && !e.target.closest('.options-btn')) {
            const detailsId = clientRow.getAttribute('data-details-id');
            if (detailsId) {
                toggleDetails(detailsId);
            }
            return;
        }

        // Handle options button clicks to stop propagation
        if (e.target.closest('.options-btn')) {
            e.stopPropagation();
        }
    });
});