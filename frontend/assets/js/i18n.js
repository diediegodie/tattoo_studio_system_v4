// i18n.js - Internationalization helper for frontend
// Loads Portuguese (pt-BR) translations and makes them available globally

let i18n = {};

// Load i18n data with fallback logic
async function loadI18n() {
    // Get browser language or default to pt-BR
    // Keep the original casing as provided by the browser, but also
    // generate several common variants so we handle filenames like
    // `pt-BR.json` and `pt-br.json` (static file serving is case-sensitive).
    const rawLang = navigator.language || 'pt-BR';
    const lower = rawLang.toLowerCase();
    const parts = rawLang.split('-');

    // Build a list of language code candidates in preferred order:
    // 1) original raw value (e.g. 'pt-BR')
    // 2) lowercased (e.g. 'pt-br')
    // 3) lower base (e.g. 'pt')
    // 4) base with upper region (e.g. 'pt-BR') — covers mixed-case filenames
    const langCodes = [];
    if (rawLang && !langCodes.includes(rawLang)) langCodes.push(rawLang);
    if (lower && !langCodes.includes(lower)) langCodes.push(lower);
    if (parts.length > 1) {
        const base = parts[0].toLowerCase();
        if (base && !langCodes.includes(base)) langCodes.push(base);
        const regionUpper = `${base}-${parts[1].toUpperCase()}`;
        if (regionUpper && !langCodes.includes(regionUpper)) langCodes.push(regionUpper);
    } else {
        const base = lower;
        if (base && !langCodes.includes(base)) langCodes.push(base);
    }

    // Always try English as final fallback
    if (!langCodes.includes('en')) langCodes.push('en');

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