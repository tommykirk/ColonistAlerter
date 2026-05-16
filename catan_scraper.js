(function() {
  const resourceMap = {
    'Grain': 'wheat',
    'Lumber': 'wood',
    'Wool': 'sheep',
    'Ore': 'ore',
    'Brick': 'brick',
    'Desert': 'desert',
  };

function parseEntry(el) {
    const span = el.querySelector('[class*="messagePart"]');
    if (!span) return null;

    const clone = span.cloneNode(true);
    clone.querySelectorAll('br').forEach(br => br.replaceWith('\n'));
    clone.querySelectorAll('hr').forEach(hr => hr.replaceWith('---'));
    clone.querySelectorAll('img').forEach(img => {
      const name = img.alt || '';
      img.replaceWith(resourceMap[name] || name);
    });
    clone.querySelectorAll('a').forEach(a => a.replaceWith(a.textContent));

    return clone.textContent?.trim() || '---';
  }

  const virtualContainer = document.querySelector('[class*="virtualContainer"]');
  const seen = new Set();
  const allLines = new Array(400); // index-keyed so order is preserved

  function harvestEl(el) {
    const item = el.closest('[class*="scrollItemContainer"]') || 
                 (el.matches('[class*="scrollItemContainer"]') ? el : null);
    if (!item) return;
    const index = parseInt(item.dataset.index);
    if (isNaN(index) || seen.has(index)) return;
    const text = parseEntry(item);
    if (text) {
      seen.add(index);
      allLines[index] = `[${index}] ${text}`;
      console.log(`[${index}] ${text}`);
    }
  }

  // MutationObserver fires when virtual list swaps in new nodes
  const observer = new MutationObserver(mutations => {
    mutations.forEach(mutation => {
      mutation.addedNodes.forEach(node => {
        if (node.nodeType !== 1) return;
        if (node.matches('[class*="scrollItemContainer"]')) harvestEl(node);
        node.querySelectorAll?.('[class*="scrollItemContainer"]').forEach(harvestEl);
      });
    });
  });

  observer.observe(virtualContainer, { childList: true, subtree: true });

  // Harvest whatever is already rendered
  virtualContainer.querySelectorAll('[class*="scrollItemContainer"]').forEach(harvestEl);

  // Scroll slowly from top to bottom
  virtualContainer.scrollTop = 0;
  virtualContainer.dispatchEvent(new Event('scroll', { bubbles: true }));

  const totalHeight = virtualContainer.scrollHeight;
  let pos = 0;

  const timer = setInterval(() => {
    pos += 150;
    virtualContainer.scrollTop = pos;
    virtualContainer.dispatchEvent(new Event('scroll', { bubbles: true }));
    virtualContainer.dispatchEvent(new WheelEvent('wheel', { deltaY: 150, bubbles: true }));

    if (pos >= totalHeight) {
      clearInterval(timer);
      setTimeout(() => {
        observer.disconnect();
        const lines = allLines.filter(Boolean);
        console.log('=== DONE. Total lines:', lines.length, '===');

        const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'catan_log.txt';
        a.click();
      }, 1000);
    }
  }, 600);
})();