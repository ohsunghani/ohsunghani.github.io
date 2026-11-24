"""Check the real plugin pipeline against page additions, deletions and exclusions."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


sys.dont_write_bytecode = True


def load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_script('health_builder', 'build-health.py')
plugin = load_script('jekyll_builder', 'build-jekyll-sitemap.py')
NS = {'s': plugin.NS}


class PluginDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.original_root = builder.ROOT
        builder.ROOT = self.root
        (self.root/'health').mkdir()
        (self.root/'health/articles.json').write_text(json.dumps({'articles': []}))

    def tearDown(self):
        builder.ROOT = self.original_root
        self.temporary.cleanup()

    def page(self, relative, canonical=None, head=''):
        path = self.root/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        link = '<link rel="canonical" href="'+canonical+'">' if canonical else ''
        path.write_text('<!doctype html><html><head><title>Fixture</title>'+link+head+
                        '</head><body><main><h1>Fixture</h1><p>Original page content.</p></main></body></html>')
        return path

    def build_and_check(self):
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*.html')}
        builder.build_search()
        expected = plugin.sitemap_entries((self.root/'sitemap.xml').read_bytes())
        feed = (self.root/'rss.xml').read_bytes()
        text_sitemap = (self.root/'sitemap.txt').read_bytes()
        plugin.build_sitemap(self.root)
        actual = plugin.sitemap_entries((self.root/'sitemap.xml').read_bytes())
        self.assertEqual(actual, expected)
        self.assertEqual((self.root/'rss.xml').read_bytes(), feed)
        self.assertEqual((self.root/'sitemap.txt').read_bytes(), text_sitemap)
        self.assertEqual(set(text_sitemap.decode('utf-8').splitlines()), set(actual))
        self.assertEqual({p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before}, before)
        self.assertEqual({item.findtext('link') for item in ET.fromstring(feed).findall('channel/item')}, set(actual))
        return actual

    def test_plugin_preserves_index_targets_dates_and_html_across_page_changes(self):
        self.page('index.html', canonical=builder.SITE)
        self.page('health/index.html', canonical=builder.SITE+'health/')
        removable = self.page('older.html')
        self.page('visit/index.html', canonical=builder.SITE+'visit/')
        self.page('new page.html', canonical=builder.SITE+'new%20page.html')
        self.page('private.html', head='<meta name="robots" content="noindex,follow">')
        self.page('private-google.html', head='<meta name="googlebot" content="none">')
        self.page('duplicate.html', canonical=builder.SITE)
        self.page('external.html', canonical='https://example.org/')
        self.page('redirect.html', head='<meta http-equiv="refresh" content="0;url=/">')
        for relative in ['404.html', 'googleabc123.html', 'naverabc123.html', '_site/copy.html', 'scripts/preview.html', 'vendor/bundle/gem-example.html']:
            self.page(relative)
        common = {builder.SITE, builder.SITE+'health/', builder.SITE+'visit/', builder.SITE+'new%20page.html'}
        self.assertEqual(set(self.build_and_check()), common | {builder.SITE+'older.html'})
        removable.unlink()
        self.page('added.html')
        self.assertEqual(set(self.build_and_check()), common | {builder.SITE+'added.html'})


if __name__ == '__main__':
    unittest.main()
