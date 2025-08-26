(function (window) {
  'use strict';

  // Small utility to safely escape CSS selectors (best-effort)
  function escapeForSelector(value) {
    if (typeof value !== 'string') value = String(value);
    if (typeof CSS !== 'undefined' && typeof CSS.escape === 'function') return CSS.escape(value);
    // Basic fallback: escape quotes and backslashes
    return value.replace(/(["'\\])/g, '\\$1');
  }

  // Remove a table row <tr data-id="...">. 
  // Accepts either a table id, a CSS selector for the table, or null/undefined to search globally.
  // Returns true when a row was removed, false otherwise.
  function removeRowById(tableIdOrSelector, itemId) {
    if (typeof itemId === 'undefined' || itemId === null) {
      throw new Error('removeRowById: itemId is required');
    }

    const escapedId = escapeForSelector(itemId);
    const rowSelector = `tr[data-id="${escapedId}"]`;

    // 1) If a table id or selector is provided, try to find the row scoped to that table
    if (tableIdOrSelector) {
      // try getElementById first (common case)
      let table = document.getElementById(tableIdOrSelector);
      if (!table) {
        // try as selector
        try {
          table = document.querySelector(tableIdOrSelector);
        } catch (e) {
          table = null;
        }
      }

      if (table) {
        const row = table.querySelector(rowSelector);
        if (row) {
          row.remove();
          return true;
        }
        return false;
      }
      // if table not found, fall through to global search
    }

    // 2) Global search fallback: remove the first matching tr[data-id]
    const globalRow = document.querySelector(rowSelector);
    if (globalRow) {
      globalRow.remove();
      return true;
    }

    return false;
  }

  // Populate a form (modal or regular) by matching input/select/textarea elements by name
  // - formId: id attribute of the form element
  // - data: object with keys matching form input names
  // Supports checkboxes, radio buttons, selects, and basic inputs
  function populateFormModal(formId, data) {
    if (!formId) throw new Error('populateFormModal: formId is required');
    const form = document.getElementById(formId);
    if (!form) return false;
    if (!data || typeof data !== 'object') return false;

    Object.keys(data).forEach((key) => {
      const value = data[key];

      // Try input/select/textarea matching by name
      const field = form.querySelector(`[name="${escapeForSelector(key)}"]`);
      if (!field) return; // skip missing fields

      const tag = field.tagName.toLowerCase();
      const type = field.type && field.type.toLowerCase();

      if (type === 'checkbox') {
        field.checked = Boolean(value);
        return;
      }

      if (type === 'radio') {
        // set the radio with matching value
        const radio = form.querySelector(`[name="${escapeForSelector(key)}"][value="${escapeForSelector(value)}"]`);
        if (radio) radio.checked = true;
        return;
      }

      if (tag === 'select') {
        try {
          field.value = value;
        } catch (e) {
          // ignore
        }
        return;
      }

      if (tag === 'textarea' || tag === 'input') {
        field.value = value == null ? '' : value;
        return;
      }

      // fallback: try setting innerText for generic nodes
      try {
        field.innerText = value == null ? '' : String(value);
      } catch (e) {
        // ignore non-writable fields
      }
    });

    return true;
  }

  // Expose helpers under a single namespace
  const domHelpers = {
    removeRowById,
    populateFormModal,
  };

  if (typeof window !== 'undefined') window.domHelpers = domHelpers;
  try {
    if (typeof module !== 'undefined' && module.exports) module.exports.domHelpers = domHelpers;
  } catch (e) {
    // ignore
  }
})(typeof window !== 'undefined' ? window : this);
