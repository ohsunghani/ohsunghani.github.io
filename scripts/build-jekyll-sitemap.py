#!/usr/bin/env python3
"""Generate the final sitemap with jekyll-sitemap without rendering the website."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://ohsunghani.github.io/'
NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
KOREA = timezone(timedelta(hours=9))


def sitemap_entries(content):
    root = ET.fromstring(content)
    if root.tag != '{'+NS+'}urlset':
        raise ValueError('Expected a standard sitemap urlset')
    entries = {}
    for node in root:
        if node.tag != '{'+NS+'}url':
            raise ValueError('Unexpected sitemap entry')
        url = node.findtext('{'+NS+'}loc')
        modified = node.findtext('{'+NS+'}lastmod')
        if not url or not url.startswith(SITE) or url in entries or not modified:
            raise ValueError('Missing, duplicate, or invalid sitemap URL/date')
        parsed = urlsplit(url)
        if parsed.query or parsed.fragment:
            raise ValueError('Sitemap URLs must not contain queries or fragments')
        changed = datetime.fromisoformat(modified)
        if changed.tzinfo:
            changed = changed.astimezone(KOREA)
        entries[url] = changed.date().isoformat()
    if not entries:
        raise ValueError('The sitemap must contain indexable pages')
    return entries


def build_sitemap(root=ROOT):
    path = root/'sitemap.xml'
    expected = sitemap_entries(path.read_bytes())
    with tempfile.TemporaryDirectory(prefix='clinic-jekyll-sitemap-') as temporary:
        work = Path(temporary)
        source = work/'source'
        source.mkdir()
        for index, (url, modified) in enumerate(expected.items()):
            permalink = urlsplit(url).path
            target = (root/unquote(permalink).lstrip('/')).resolve()
            if target.is_dir():
                target /= 'index.html'
            if not target.is_relative_to(root.resolve()) or not target.is_file():
                raise ValueError('Sitemap target does not exist: '+url)
            # Only metadata stubs go through Jekyll. Its HTML output is discarded.
            metadata = ('---\npermalink: '+json.dumps(permalink)+'\n'
                        'last_modified_at: '+json.dumps(modified+'T00:00:00+09:00')+'\n---\n')
            (source/f'page-{index:05}.html').write_text(metadata)
        config = work/'_config.yml'
        config.write_text(json.dumps({
            'url': SITE.rstrip('/'), 'baseurl': '', 'timezone': 'Asia/Seoul',
            'plugins': ['jekyll-sitemap'], 'quiet': True,
        }))
        destination = work/'output'
        subprocess.run([
            'bundle', 'exec', 'jekyll', 'build', '--source', str(source),
            '--destination', str(destination), '--config', str(config),
        ], cwd=root, env=dict(os.environ, BUNDLE_GEMFILE=str(ROOT/'Gemfile')), check=True)
        generated = (destination/'sitemap.xml').read_bytes()
        actual = sitemap_entries(generated)
        if actual != expected:
            missing = sorted(expected.keys()-actual.keys())
            unexpected = sorted(actual.keys()-expected.keys())
            changed = [url for url in expected.keys() & actual.keys() if expected[url] != actual[url]]
            raise ValueError('Jekyll sitemap differs from the indexable pages: '+json.dumps({
                'missing': missing[:5], 'unexpected': unexpected[:5], 'changed_dates': changed[:5],
            }))
        path.write_bytes(generated)
    print(f'Built sitemap with jekyll-sitemap 1.4.0 for {len(expected)} indexable pages.')


if __name__ == '__main__':
    build_sitemap()
