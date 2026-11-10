(() => {
  'use strict';

  document.documentElement.classList.add('js-enabled');

  const menuToggle = document.querySelector('.menu-toggle');
  const navigation = document.querySelector('.site-nav');

  if (menuToggle && navigation) {
    const setMenuOpen = (open) => {
      navigation.classList.toggle('is-open', open);
      menuToggle.setAttribute('aria-expanded', String(open));
      menuToggle.setAttribute('aria-label', open ? '메뉴 닫기' : '메뉴 열기');
    };

    menuToggle.addEventListener('click', () => {
      setMenuOpen(menuToggle.getAttribute('aria-expanded') !== 'true');
    });
    navigation.addEventListener('click', (event) => {
      if (event.target.closest('a')) setMenuOpen(false);
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && menuToggle.getAttribute('aria-expanded') === 'true') {
        setMenuOpen(false);
        menuToggle.focus();
      }
    });

    const desktop = window.matchMedia('(min-width: 1001px)');
    const closeOnDesktop = (event) => {
      if (event.matches) setMenuOpen(false);
    };
    if (desktop.addEventListener) {
      desktop.addEventListener('change', closeOnDesktop);
    } else if (desktop.addListener) {
      desktop.addListener(closeOnDesktop);
    }
  }

  const search = document.querySelector('[data-faq-search]');
  const questions = [...document.querySelectorAll('[data-faq-category]')];

  if (questions.length) {
    const toolbar = document.querySelector('.faq-toolbar');
    const filters = [...document.querySelectorAll('[data-faq-filter]')];
    const groups = [...document.querySelectorAll('[data-faq-group]')];
    const resultCount = document.querySelector('[data-faq-count]');
    const emptyMessage = document.querySelector('[data-faq-empty]');
    const normalize = (value) => String(value).normalize('NFKC').toLocaleLowerCase('ko-KR').replace(/\s+/g, '');
    const searchableQuestions = new Map(questions.map((question) => [question, normalize(question.textContent)]));
    let category = 'all';

    const updateResults = () => {
      const query = normalize(search ? search.value : '');
      let visibleCount = 0;

      questions.forEach((question) => {
        const matchesCategory = category === 'all' || question.dataset.faqCategory === category;
        const matchesSearch = !query || searchableQuestions.get(question).includes(query);
        question.hidden = !(matchesCategory && matchesSearch);
        if (!question.hidden) visibleCount += 1;
      });
      groups.forEach((group) => {
        group.hidden = !group.querySelector('[data-faq-category]:not([hidden])');
      });
      filters.forEach((filter) => {
        filter.setAttribute('aria-pressed', String(filter.dataset.faqFilter === category));
      });
      if (resultCount) {
        resultCount.textContent = category === 'all' && !query
          ? `전체 ${questions.length}개의 질문`
          : `${questions.length}개 중 ${visibleCount}개의 질문`;
      }
      if (emptyMessage) emptyMessage.hidden = visibleCount !== 0;
    };

    if (search) search.addEventListener('input', updateResults);
    filters.forEach((filter) => {
      filter.addEventListener('click', () => {
        category = filter.dataset.faqFilter;
        updateResults();
      });
    });

    const revealHashTarget = (hash, shouldScroll) => {
      if (!hash || hash === '#') return;
      let id;
      try {
        id = decodeURIComponent(hash.slice(1));
      } catch {
        return;
      }
      const target = document.getElementById(id);
      if (!target || !target.closest('[data-faq-group], [data-faq-category]')) return;
      category = 'all';
      if (search) search.value = '';
      updateResults();
      let ancestor = target;
      while (ancestor && ancestor !== document.body) {
        if (ancestor.tagName === 'DETAILS') ancestor.open = true;
        ancestor = ancestor.parentElement;
      }
      if (shouldScroll) {
        window.requestAnimationFrame(() => target.scrollIntoView({ block: 'start' }));
      }
    };

    updateResults();
    if (toolbar) toolbar.hidden = false;
    revealHashTarget(window.location.hash, true);
    window.addEventListener('hashchange', () => revealHashTarget(window.location.hash, true));
    document.addEventListener('click', (event) => {
      const link = event.target.closest('a[href^="#"]');
      if (link) revealHashTarget(link.getAttribute('href'), false);
    });
  }

  const copyWithSelection = (address) => {
    const previousFocus = document.activeElement;
    const temporaryField = document.createElement('textarea');
    temporaryField.value = address;
    temporaryField.readOnly = true;
    temporaryField.tabIndex = -1;
    temporaryField.setAttribute('aria-hidden', 'true');
    temporaryField.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0;';
    document.body.appendChild(temporaryField);
    let copied = false;
    try {
      temporaryField.select();
      temporaryField.setSelectionRange(0, address.length);
      copied = document.execCommand('copy') === true;
    } catch {
      copied = false;
    } finally {
      temporaryField.remove();
      if (previousFocus && typeof previousFocus.focus === 'function') {
        previousFocus.focus({ preventScroll: true });
      }
    }
    return copied;
  };

  document.querySelectorAll('[data-copy-address]').forEach((button) => {
    button.addEventListener('click', async () => {
      const address = button.dataset.copyAddress || button.value || '';
      const status = button.parentElement.querySelector('[data-copy-status]') || document.querySelector('[data-copy-status]');
      if (!address) return;
      let copied = false;
      if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        try {
          await navigator.clipboard.writeText(address);
          copied = true;
        } catch {
          copied = false;
        }
      }
      if (!copied) copied = copyWithSelection(address);
      if (status) {
        status.textContent = copied
          ? '주소가 복사되었습니다.'
          : '주소를 길게 누르거나 선택해 복사해 주세요.';
      }
    });
  });
})();
