// i18n.js - Internationalization helper for frontend
// Loads Portuguese (pt-BR) translations and makes them available globally

let i18n = {};

// Load i18n data with fallback logic
async function loadI18n() {
    // Get browser language or default to pt-BR
    const browserLang = (navigator.language || 'pt-BR').toLowerCase();
    const langCodes = [browserLang];

    // Add fallback language codes
    if (browserLang.includes('-')) {
        // If it's a regional variant (e.g., pt-BR), add the base language (pt)
        langCodes.push(browserLang.split('-')[0]);
    }

    // Always try English as final fallback
    if (!langCodes.includes('en')) {
        langCodes.push('en');
    }

    let loaded = false;

    for (const lang of langCodes) {
        try {
            console.log(`🔄 Trying to load i18n file: /assets/i18n/${lang}.json`);
            const response = await fetch(`/assets/i18n/${lang}.json`);

            if (response.ok) {
                i18n = await response.json();
                console.log(`✅ i18n loaded successfully from ${lang}.json`);
                loaded = true;
                break;
            } else if (response.status === 404) {
                console.warn(`⚠️ Could not load i18n file for ${lang}, trying next fallback...`);
            } else {
                console.warn(`⚠️ Unexpected response (${response.status}) for ${lang}.json, trying next fallback...`);
            }
        } catch (error) {
            console.warn(`⚠️ Error loading ${lang}.json:`, error.message);
        }
    }

    if (!loaded) {
        console.warn('⚠️ All i18n files failed to load, using hardcoded defaults');
        // Fallback to hardcoded values
        i18n = {
            "cliente": "Cliente",
            "clientes": "Clientes",
            "artista": "Artista",
            "artistas": "Artistas",
            "sessao": "Sessão",
            "sessoes": "Sessões",
            "pagamento": "Pagamento",
            "pagamentos": "Pagamentos",
            "comissao": "Comissão",
            "comissoes": "Comissões",
            "gasto": "Gasto",
            "gastos": "Gastos",
            "historico": "Histórico",
            "extrato": "Extrato",
            "financeiro": "Financeiro",
            "alternar": "Alternar"
        };
    }

    // Make i18n available globally
    window.i18n = i18n;
}

// Helper function to get translated text
function t(key) {
    return i18n[key] || key;
}

// Initialize i18n when DOM is ready
document.addEventListener('DOMContentLoaded', loadI18n);

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { loadI18n, t };
}