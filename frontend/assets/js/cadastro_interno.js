// cadastro_interno.js - Form handling for internal artist registration

// Helper: fetch CSRF token from <meta name="csrf-token">
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : null;
}

// Define getStatusHelper for consistent flash message handling (matching Sessões/Financeiro)
function getStatusHelper() {
    return typeof window.showStatus === 'function' ? window.showStatus : function (msg, ok) {
        try {
            if (ok) {
                if (window.notifySuccess) window.notifySuccess(msg);
            } else {
                if (window.notifyError) window.notifyError(msg);
            }
        } catch (e) { console.log(msg); }
    };
}

document.getElementById('cadastro-artista-form').addEventListener('submit', function (e) {
    e.preventDefault();

    const name = document.getElementById('artista').value.trim();
    const email = document.getElementById('email').value.trim();

    if (!name) {
        getStatusHelper()('Nome do artista é obrigatório.', false);
        return;
    }

    // Show loading state
    const submitButton = this.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.textContent = 'Cadastrando...';
    submitButton.disabled = true;

    // Prepare data
    const data = { name: name };
    if (email) {
        data.email = email;
    }

    // Send request to SOLID-compliant artist endpoint
    fetch('/artist/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            ...(getCsrfToken() ? { 'X-CSRFToken': getCsrfToken(), 'X-CSRF-Token': getCsrfToken() } : {})
        },
        body: JSON.stringify(data)
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                getStatusHelper()(`Artista "${data.artist.name}" cadastrado com sucesso!`, true);
                // Clear form
                document.getElementById('artista').value = '';
                document.getElementById('email').value = '';

                // Use same 1-second delay as reference implementations
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                getStatusHelper()(data.error || 'Erro ao cadastrar artista.', false);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            getStatusHelper()('Erro interno. Tente novamente.', false);
        })
        .finally(() => {
            // Reset button state
            submitButton.textContent = originalText;
            submitButton.disabled = false;
        });
});

// Edit Artist Functionality
function editArtist(artistId) {
    // Use standard status helper instead of showMessage
    getStatusHelper()('Carregando dados do artista...', true);

    fetch(`/artist/${artistId}`, {
        method: 'GET',
        headers: {
            'Accept': 'application/json'
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const artist = data.artist;

                // Create form content for unified modal
                const formContent = `
                    <form id="edit-artist-form">
                        <input type="hidden" id="edit-artist-id" name="id" value="${artist.id}">
                        <label for="edit-artist-name">Nome do artista</label>
                        <input type="text" id="edit-artist-name" name="name" required class="input-full-mb" value="${artist.name || ''}">

                        <label for="edit-artist-email">Email (opcional)</label>
                        <input type="email" id="edit-artist-email" name="email" class="input-full-mb" value="${artist.email || ''}">
                    </form>
                `;

                // Open modal with standard parameters (matching Sessões/Financeiro)
                openCustomModal({
                    title: 'Editar Artista',
                    content: formContent,
                    confirmText: 'Salvar',
                    cancelText: 'Cancelar',
                    onConfirm: async function () {
                        const form = document.getElementById('edit-artist-form');
                        if (!form) return;

                        // Use standard status helper instead of showMessage
                        getStatusHelper()('Salvando alterações...', true);

                        const formData = new FormData(form);
                        const artistId = formData.get('id');
                        const name = formData.get('name').trim();
                        const email = formData.get('email').trim();

                        if (!name) {
                            getStatusHelper()('Nome do artista é obrigatório.', false);
                            return;
                        }

                        const data = { name: name };
                        if (email) {
                            data.email = email;
                        }

                        try {
                            const response = await fetch(`/artist/${artistId}`, {
                                method: 'PUT',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'Accept': 'application/json',
                                    ...(getCsrfToken() ? { 'X-CSRFToken': getCsrfToken(), 'X-CSRF-Token': getCsrfToken() } : {})
                                },
                                body: JSON.stringify(data)
                            });

                            const result = await response.json();

                            if (result.success) {
                                // Use standard success handling (matching Sessões/Financeiro)
                                getStatusHelper()('Artista atualizado com sucesso!', true);
                                closeModal();
                                // Use same 1-second delay as reference implementations
                                setTimeout(() => {
                                    window.location.reload();
                                }, 1000);
                            } else {
                                getStatusHelper()(result.error || 'Erro ao atualizar artista.', false);
                            }
                        } catch (error) {
                            console.error('Error:', error);
                            getStatusHelper()('Erro interno. Tente novamente.', false);
                        }
                    }
                });
            } else {
                getStatusHelper()(data.error || 'Erro ao carregar artista.', false);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            getStatusHelper()('Erro interno. Tente novamente.', false);
        });
}

// Delete Artist Functionality
async function deleteArtist(artistId) {
    console.log('[DEBUG] deleteArtist called with id:', artistId);

    // Use the unified confirmation modal if available
    // Require the unified confirmAction; if missing, refuse to proceed
    if (typeof window.confirmAction === 'function') {
        console.log('[DEBUG] deleteArtist delegating to window.confirmAction with id:', artistId);
        const confirmed = await window.confirmAction('Tem certeza que deseja excluir este artista?');
        console.log('[DEBUG] deleteArtist user confirmation:', confirmed);
        if (!confirmed) {
            console.log('[DEBUG] deleteArtist cancelled by user');
            return;
        }
    } else {
        console.error('[DEBUG] window.confirmAction not available in cadastro_interno.html — refusing to delete artist', artistId);
        return;
    }

    // Use standard status helper instead of showMessage
    getStatusHelper()('Excluindo artista...', true);

    try {
        const response = await fetch(`/artist/${artistId}`, {
            method: 'DELETE',
            headers: {
                'Accept': 'application/json',
                ...(getCsrfToken() ? { 'X-CSRFToken': getCsrfToken(), 'X-CSRF-Token': getCsrfToken() } : {})
            }
        });

        const data = await response.json();

        if (data.success) {
            console.log('[DEBUG] deleteArtist success response:', data);
            getStatusHelper()('Artista excluído com sucesso!', true);
            try { if (typeof closeModal === 'function') closeModal(); } catch (e) { }
            // Use same 1-second delay as reference implementations
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            console.log('[DEBUG] deleteArtist failed response:', data);
            getStatusHelper()(data.error || 'Erro ao excluir artista.', false);
        }
    } catch (error) {
        console.error('Error:', error);
        getStatusHelper()('Erro interno. Tente novamente.', false);
    }
}

// Event delegation for edit and delete buttons
document.addEventListener('click', function (e) {
    const editBtn = e.target.closest('.edit-artist-btn');
    if (editBtn) {
        e.preventDefault();
        const artistId = editBtn.getAttribute('data-id');
        if (artistId) {
            editArtist(artistId);
        }
        return;
    }

    const deleteBtn = e.target.closest('.delete-artist-btn');
    if (deleteBtn) {
        e.preventDefault();
        const artistId = deleteBtn.getAttribute('data-id');
        if (artistId) {
            deleteArtist(artistId);
        }
        return;
    }
});