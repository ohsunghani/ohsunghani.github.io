#!/usr/bin/env python3
"""Keep the clinic's primary services in static HTML navigation."""
from pathlib import Path
from html import escape
import re

ROOT = Path(__file__).resolve().parents[1]
NAV_ITEMS = (
    ('pain-pharmacopuncture.html', '통증·약침'),
    ('traffic-accident.html', '교통사고'),
    ('gongjindan.html', '공진단·한약'),
    ('about.html', '의료진 소개'),
    ('health/', '건강칼럼'),
    ('info.html', '진료 안내'),
)


def sync_navigation():
    changed = 0
    for path in ROOT.rglob('*.html'):
        relative = path.relative_to(ROOT)
        if any(part.startswith('.') or part in ('_site', 'vendor', 'node_modules') for part in relative.parts):
            continue
        original = path.read_text()
        if '<nav class="site-nav"' not in original:
            continue
        prefix = '../' * (len(relative.parts) - 1)
        links = []
        for target, label in NAV_ITEMS:
            current = relative.as_posix() == target or (relative.as_posix() == 'health/index.html' and target == 'health/')
            links.append('<a href="' + prefix + target + '"' + (' aria-current="page"' if current else '') + '>' + label + '</a>')
        navigation = '<nav class="site-nav" id="site-nav" aria-label="주 메뉴">' + ''.join(links) + '</nav>'
        updated, count = re.subn(r'<nav class="site-nav"[^>]*>.*?</nav>', lambda _: navigation, original, flags=re.S)
        assert count == 1, str(relative)
        support = '<div class="footer-support"><nav class="footer-links" aria-label="추가 안내"><a href="' + escape(prefix + 'faq.html', quote=True) + '"' + (' aria-current="page"' if relative.as_posix() == 'faq.html' else '') + '>자주 묻는 질문</a></nav><span class="copyright">© 오성한의원</span></div>'
        if '<div class="footer-support">' in updated:
            updated, count = re.subn(r'<div class="footer-support">.*?<span class="copyright">© 오성한의원</span></div>', lambda _: support, updated, flags=re.S)
        else:
            updated, count = re.subn(r'<span class="copyright">© 오성한의원</span>', lambda _: support, updated)
        assert count == 1, str(relative)
        if updated != original:
            path.write_text(updated)
            changed += 1
    print(f'Synchronized primary service navigation in {changed} pages.')


if __name__ == '__main__':
    sync_navigation()
