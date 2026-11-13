"""Exercise discovery behavior without changing the real website."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('site_builder', Path(__file__).with_name('build-health.py'))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
NS = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.original_root = builder.ROOT
        builder.ROOT = self.root
        (self.root/'health').mkdir()
        self.catalog([])
        self.page('index.html', canonical=builder.SITE)

    def tearDown(self):
        builder.ROOT = self.original_root
        self.temp.cleanup()

    def catalog(self, articles):
        (self.root/'health/articles.json').write_text(json.dumps({'updated': '2026-11-12', 'articles': articles}))

    def page(self, path, canonical=None, head='', body='<main><h1>Page</h1><p>Complete content.</p></main>'):
        target = self.root/path
        target.parent.mkdir(parents=True, exist_ok=True)
        link = '<link rel="canonical" href="'+canonical+'">' if canonical else ''
        target.write_text('<!doctype html><html><head><title>Test page</title>'+link+head+'</head><body>'+body+'</body></html>')
        return target

    def urls(self):
        return {n.text for n in ET.parse(self.root/'sitemap.xml').findall('s:url/s:loc', NS)}

    def items(self):
        return ET.parse(self.root/'rss.xml').findall('channel/item')

    def test_addition_and_deletion_update_both_feeds(self):
        page = self.page('new.html')
        builder.build_search()
        self.assertIn(builder.SITE+'new.html', self.urls())
        page.unlink()
        builder.build_search()
        self.assertEqual(self.urls(), {builder.SITE})
        self.assertEqual({i.findtext('link') for i in self.items()}, self.urls())

    def test_non_index_targets_are_excluded(self):
        self.page('private.html', head='<meta name="robots" content="NOINDEX, follow">')
        self.page('private-google.html', head='<meta name="googlebot" content="none">')
        self.page('redirect.html', head='<meta http-equiv="refresh" content="0;url=/">')
        self.page('duplicate.html', canonical=builder.SITE)
        self.page('external.html', canonical='https://example.org/')
        for path in ['404.html', 'naverabc123.html', 'googleabc123.html', '_site/copied.html', '.private/page.html', 'scripts/preview.html']:
            self.page(path)
        builder.build_search()
        self.assertEqual(self.urls(), {builder.SITE})

    def test_encoded_paths_uppercase_tags_and_directory_canonical(self):
        path = self.page('new page.html', canonical=builder.SITE+'new%20page.html', body='<main><p>Full text.</p><a href="index.html">Home</a></main>')
        path.write_text(path.read_text().replace('<title>', '<TITLE>').replace('</title>', '</TITLE>').replace('<main>', '<MAIN>').replace('</main>', '</MAIN>'))
        self.page('visit/index.html', canonical=builder.SITE+'visit/')
        builder.build_search()
        self.assertEqual(self.urls(), {builder.SITE, builder.SITE+'new%20page.html', builder.SITE+'visit/'})
        item = next(i for i in self.items() if i.findtext('link').endswith('new%20page.html'))
        self.assertIn('Full text.', item.findtext('description'))
        self.assertIn('href="'+builder.SITE+'index.html"', item.findtext('description'))
        self.assertIsNone(item.find('pubDate'))

    def test_rss_uses_web_dates_and_complete_article_content(self):
        articles = [
            {'slug': 'older', 'category': 'pain', 'title': 'Older', 'website_published': '2026-09-03', 'published_date': '2026-11-12'},
            {'slug': 'newer', 'category': 'pain', 'title': 'Newer', 'website_published': '2026-11-12', 'published_date': '2025-01-01'},
        ]
        self.catalog(articles)
        for a in articles:
            self.page('health/'+a['slug']+'.html', body='<main><article class="article-body"><p>First paragraph.</p><ul><li>List content.</li></ul><p>Last paragraph.</p></article></main>')
        builder.build_search()
        items = [i for i in self.items() if i.find('pubDate') is not None]
        self.assertEqual([i.findtext('title') for i in items], ['Newer', 'Older'])
        for item, expected in zip(items, ['2026-11-12', '2026-09-03']):
            self.assertEqual(parsedate_to_datetime(item.findtext('pubDate')).date().isoformat(), expected)
            self.assertIn('First paragraph.', item.findtext('description'))
            self.assertIn('List content.', item.findtext('description'))
            self.assertIn('Last paragraph.', item.findtext('description'))

    def test_lastmod_uses_git_date_in_korea(self):
        subprocess.run(['git', 'init', '-q'], cwd=self.root, check=True)
        subprocess.run(['git', 'add', 'index.html'], cwd=self.root, check=True)
        env = dict(os.environ, GIT_AUTHOR_DATE='2026-11-10T20:00:00+0000', GIT_COMMITTER_DATE='2026-11-10T20:00:00+0000')
        subprocess.run(['git', '-c', 'user.name=Search Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'Fixture'], cwd=self.root, env=env, check=True)
        self.assertEqual(builder.page_last_modified(self.root/'index.html'), '2026-11-11')

    def philosophy_fixture(self):
        article = {
            'slug': 'verified-philosophy', 'category': 'philosophy', 'title': 'Verified philosophy',
            'source_url': 'https://blog.naver.com/ohsunghani/224436078434',
            'source_title': 'Verified original', 'published_date': '2026-10-27',
            'website_published': '2026-11-13',
        }
        (self.root/'scripts').mkdir(exist_ok=True)
        registry = {'blog_id': 'ohsunghani', 'category_no': 25, 'sources': [
            {'url': article['source_url'], 'title': article['source_title'], 'published_date': article['published_date']}
        ]}
        (self.root/'scripts/philosophy-sources.json').write_text(json.dumps(registry))
        return article

    def test_philosophy_rejects_other_sources_before_both_build_modes(self):
        article = self.philosophy_fixture()
        for url in ['https://blog.naver.com/ohsunghani/223215818324', 'https://ohsunghani.tistory.com/66']:
            self.catalog([dict(article, source_url=url)])
            for build in [builder.build, builder.build_search]:
                with self.subTest(url=url, mode=build.__name__):
                    with self.assertRaisesRegex(ValueError, 'Naver category 25'):
                        build()
        self.assertFalse((self.root/'sitemap.xml').exists())

    def test_philosophy_rejects_wrong_original_metadata(self):
        article = self.philosophy_fixture()
        for changes in [{'source_title': 'Unrelated rewritten original'}, {'published_date': '2026-11-13'}]:
            self.catalog([dict(article, **changes)])
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ValueError, 'metadata does not match'):
                    builder.build_search()

    def test_philosophy_accepts_verified_category_original(self):
        article = self.philosophy_fixture()
        self.catalog([article])
        self.page('health/'+article['slug']+'.html', body='<main><article class="article-body"><p>Faithful summary.</p></article></main>')
        builder.build_search()
        self.assertEqual(self.urls(), {builder.SITE, builder.SITE+'health/'+article['slug']+'.html'})
        item = next(i for i in self.items() if i.findtext('category') == '진료 철학')
        self.assertEqual(item.findtext('title'), article['title'])


if __name__ == '__main__':
    unittest.main()
