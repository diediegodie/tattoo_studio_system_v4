// agenda.js - Agenda page functionality

function toggleDetails(detailsId) {
    const detailsElement = document.getElementById(detailsId);
    if (detailsElement) {
        detailsElement.classList.toggle('hidden');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Event delegation for action buttons
    document.addEventListener('click', function(e) {
        const paidButton = e.target.closest('.button-success');
        const unpaidButton = e.target.closest('.create-session-btn');
        const genericOptionButton = e.target.closest('.options-btn');

        if (paidButton || unpaidButton || genericOptionButton) {
            // Strengthened isolation: prevent default anchor behavior (we will redirect explicitly)
            e.preventDefault();
            e.stopPropagation();

            // Explicit redirect logic for paid button
            if (paidButton) {
                const url = paidButton.getAttribute('data-redirect-url') || paidButton.getAttribute('href');
                if (url) {
                    window.location.href = url;
                }
                return;
            }

            // Explicit redirect logic for unpaid button (payment registration flow)
            if (unpaidButton) {
                const url = unpaidButton.getAttribute('href');
                if (url) {
                    window.location.href = url;
                }
                return;
            }

            // Any other option buttons just isolate click
            return;
        }
        // Row click behavior (collapse toggle) remains default (handled elsewhere)
    });
});