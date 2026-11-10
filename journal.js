(() => {
  'use strict';

  const grid = document.querySelector('[data-journal-grid]');
  const search = document.querySelector('[data-journal-search]');
  if (!grid || !search) return;

  const cards = [...grid.querySelectorAll('[data-journal-entry]')];
  const filters = [...document.querySelectorAll('[data-journal-filter]')];
  const toolbar = document.querySelector('[data-journal-tools]');
  const resultCount = document.querySelector('[data-journal-count]');
  const emptyMessage = document.querySelector('[data-journal-empty]');
  const clearButton = document.querySelector('[data-journal-clear]');
  const normalize = (value) => String(value).normalize('NFKC').toLocaleLowerCase('ko-KR').replace(/\s+/g, '');
  const searchableCards = new Map(cards.map((card) => [card, normalize(`${card.textContent} ${card.dataset.search || ''}`)]));
  let category = 'all';

  const updateResults = () => {
    const query = normalize(search.value);
    let visibleCount = 0;
    cards.forEach((card) => {
      const matchesCategory = category === 'all' || card.dataset.category === category;
      const matchesQuery = !query || searchableCards.get(card).includes(query);
      card.hidden = !(matchesCategory && matchesQuery);
      if (!card.hidden) visibleCount += 1;
    });
    filters.forEach((filter) => filter.setAttribute('aria-pressed', String(filter.dataset.journalFilter === category)));
    if (resultCount) {
      resultCount.textContent = category === 'all' && !query
        ? `전체 ${cards.length}개의 칼럼`
        : `전체 ${cards.length}개 중 ${visibleCount}개의 칼럼`;
    }
    if (emptyMessage) emptyMessage.hidden = visibleCount !== 0;
    if (clearButton) clearButton.hidden = category === 'all' && !query;
  };

  search.addEventListener('input', updateResults);
  filters.forEach((filter) => {
    filter.addEventListener('click', () => {
      category = filter.dataset.journalFilter;
      updateResults();
    });
  });
  if (clearButton) {
    clearButton.addEventListener('click', () => {
      search.value = '';
      category = 'all';
      updateResults();
      search.focus();
    });
  }

  updateResults();
  if (toolbar) toolbar.hidden = false;
})();
