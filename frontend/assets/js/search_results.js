document.addEventListener('DOMContentLoaded', function () {
  const tokens = (document.body && document.body.dataset && document.body.dataset.searchQuery
    ? document.body.dataset.searchQuery
    : '').toLowerCase().split(/\s+/).filter(t => t.length > 0);
  if (!tokens.length) return;

  function highlightElement(element) {
    element.childNodes.forEach(node => {
      if (node.nodeType === Node.TEXT_NODE) {
        if (node.parentNode.tagName === 'STRONG') return;
        let text = node.textContent;
        let hasChanges = false;
        tokens.forEach(token => {
          const escapedToken = token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
          const regex = new RegExp('(' + escapedToken + ')', 'gi');
          if (regex.test(text)) {
            text = text.replace(regex, '<mark>$1</mark>');
            hasChanges = true;
          }
        });
        if (hasChanges) {
          const span = document.createElement('span');
          span.innerHTML = text;
          node.parentNode.replaceChild(span, node);
        }
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        highlightElement(node);
      }
    });
  }

  document.querySelectorAll('.search-result p').forEach(p => {
    highlightElement(p);
  });
});
