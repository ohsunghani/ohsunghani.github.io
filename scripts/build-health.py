#!/usr/bin/env python3
"""Render the clinic's static article archive from health/articles.json."""
from pathlib import Path
from html import escape, unescape
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, unquote, quote
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://ohsunghani.github.io/'
VERSION = '20261110-compact1'
RSS_LINK = '<link rel="alternate" type="application/rss+xml" title="오성한의원 홈페이지 소식" href="'+SITE+'rss.xml">'
LABELS = {
    'pain': '통증 · 자세', 'accident': '교통사고',
    'treatment': '치료 · 내원 안내', 'herbal': '한약 · 공진단',
    'lifestyle': '생활건강', 'philosophy': '진료 철학',
}
ARROW = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6"/></svg>'
SEARCH = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg>'

def attr(text):
    return escape(str(text), quote=True)

def rss_date(value):
    # The catalog records calendar dates in Korea, without a publication time.
    return format_datetime(datetime.fromisoformat(value).replace(tzinfo=timezone(timedelta(hours=9))))

class SearchMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonicals = []
        self.noindex = False
        self.redirect = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link' and 'canonical' in (attrs.get('rel') or '').lower().split():
            self.canonicals.append(attrs.get('href') or '')
        if tag == 'meta':
            name = (attrs.get('name') or '').lower()
            tokens = re.split(r'[,;\s]+', (attrs.get('content') or '').lower())
            if name in {'robots', 'googlebot', 'naverbot', 'yeti'} and {'noindex', 'none'} & set(tokens):
                self.noindex = True
            self.redirect |= (attrs.get('http-equiv') or '').lower() == 'refresh'

def page_last_modified(path):
    result = subprocess.run(['git', 'log', '-1', '--format=%cI', '--', str(path.relative_to(ROOT))], cwd=ROOT, capture_output=True, text=True)
    value = result.stdout.strip()
    changed = datetime.fromisoformat(value) if result.returncode == 0 and value else datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    return changed.astimezone(timezone(timedelta(hours=9))).date().isoformat()

def validate_philosophy_sources(articles):
    """Only the clinic's verified Naver category 25 posts qualify as philosophy."""
    selected = [a for a in articles if a.get('category') == 'philosophy']
    if not selected:
        return
    registry = json.loads((ROOT/'scripts/philosophy-sources.json').read_text())
    if registry.get('blog_id') != 'ohsunghani' or registry.get('category_no') != 25:
        raise ValueError('Invalid philosophy source registry')
    sources = {row['url']: row for row in registry['sources']}
    for article in selected:
        source = sources.get(article.get('source_url'))
        if source is None:
            raise ValueError('Philosophy requires a verified Naver category 25 source: '+article['slug'])
        if article.get('source_title') != source['title'] or article.get('published_date') != source['published_date']:
            raise ValueError('Philosophy source metadata does not match the verified original: '+article['slug'])

def build_search():
    """Rebuild discovery files from existing, indexable HTML; remove stale URLs."""
    data = json.loads((ROOT/'health/articles.json').read_text())
    validate_philosophy_sources(data['articles'])
    ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    ET.register_namespace('', ns)
    sitemap = ET.Element('{'+ns+'}urlset')
    seen = set()
    for path in sorted(ROOT.rglob('*.html'), key=lambda p: (p != ROOT/'index.html', str(p))):
        relative = path.relative_to(ROOT)
        if any(part.startswith(('.', '_')) or part in {'scripts', 'node_modules'} for part in relative.parts):
            continue
        if path.name == '404.html' or re.fullmatch(r'(?:google|naver)[a-zA-Z0-9]+\.html', path.name):
            continue
        metadata = SearchMetadata()
        metadata.feed(path.read_text())
        if metadata.noindex or metadata.redirect:
            continue
        assert len(metadata.canonicals) <= 1, 'Multiple canonical URLs: '+str(relative)
        expected = SITE + ('' if relative.as_posix() == 'index.html' else quote(relative.as_posix(), safe='/'))
        canonical = urljoin(expected, metadata.canonicals[0]) if metadata.canonicals else expected
        parsed = urlsplit(canonical)
        if parsed.netloc != urlsplit(SITE).netloc:
            continue  # An explicit canonical on another site is not an index target here.
        assert parsed.scheme == 'https' and not parsed.query and not parsed.fragment, 'Invalid canonical URL: '+canonical
        target = (ROOT/unquote(parsed.path).lstrip('/')).resolve()
        if target.is_dir():
            target /= 'index.html'
        assert target.is_relative_to(ROOT) and target.exists(), 'Canonical target is missing: '+canonical
        if target != path.resolve():
            continue  # A local duplicate belongs under the canonical page's URL only.
        assert canonical not in seen, 'Duplicate canonical URL: '+canonical
        seen.add(canonical)
        node = ET.SubElement(sitemap, '{'+ns+'}url')
        ET.SubElement(node, '{'+ns+'}loc').text = canonical
        ET.SubElement(node, '{'+ns+'}lastmod').text = page_last_modified(path)
    assert seen, 'No indexable site pages found'
    ET.indent(sitemap, space='  ')
    (ROOT/'sitemap.xml').write_bytes(ET.tostring(sitemap, encoding='utf-8', xml_declaration=True)+b'\n')
    last_changed = max(node.find('{'+ns+'}lastmod').text for node in sitemap)
    write_rss(data['articles'], sitemap, last_changed)
    print(f'Built sitemap and sitewide RSS for {len(seen)} indexable pages.')

def write_rss(catalog, sitemap, updated):
    """Publish the complete, rendered content of every page in the sitemap."""
    atom = 'http://www.w3.org/2005/Atom'
    ET.register_namespace('atom', atom)
    feed = ET.Element('rss', {'version': '2.0'})
    channel = ET.SubElement(feed, 'channel')
    ET.SubElement(channel, 'title').text = '오성한의원 홈페이지 소식'
    ET.SubElement(channel, 'link').text = SITE
    ET.SubElement(channel, 'description').text = '파주 봉일천 오성한의원의 진료 안내, 의료진 소개, 자주 묻는 질문과 건강칼럼을 전합니다.'
    ET.SubElement(channel, 'language').text = 'ko-kr'
    ET.SubElement(channel, 'lastBuildDate').text = rss_date(updated)
    ET.SubElement(channel, '{'+atom+'}link', {'href': SITE+'rss.xml', 'rel': 'self', 'type': 'application/rss+xml'})
    by_url = {SITE+'health/'+a['slug']+'.html': (i, a) for i, a in enumerate(catalog)}
    ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    urls = [node.find('{'+ns+'}loc').text for node in sitemap]
    assert urls and len(set(urls)) == len(urls), 'Empty or duplicate RSS pages'
    core = [url for url in urls if url not in by_url]
    columns = sorted((url for url in urls if url in by_url), key=lambda url: (by_url[url][1].get('website_published', ''), by_url[url][0]), reverse=True)
    for url in core+columns:
        assert url.startswith(SITE), 'Unexpected RSS domain'
        path = (ROOT/(unquote(url[len(SITE):]) or 'index.html')).resolve()
        assert path.is_relative_to(ROOT), 'Unexpected RSS page path'
        if path.is_dir():
            path /= 'index.html'
        page = path.read_text()
        article = by_url[url][1] if url in by_url else None
        pattern = r'<article class="article-body">(.*?)</article>' if article else r'<main\b[^>]*>(.*?)</main>'
        match = re.search(pattern, page, re.S|re.I)
        if not match and not article:
            match = re.search(r'<body\b[^>]*>(.*?)</body>', page, re.S|re.I)
        assert match and match.group(1).strip(), 'Missing RSS page content: '+url
        body = re.sub(r'<(script|style|svg)\b[^>]*>.*?</\1>', '', match.group(1), flags=re.S|re.I)
        body = re.sub(r'''\b(href|src)=(['"])(.*?)\2''', lambda m: m[1]+'="'+attr(urljoin(url, unescape(m[3])))+'"', body, flags=re.S|re.I)
        title_match = re.search(r'<title\b[^>]*>(.*?)</title>', page, re.S|re.I)
        assert title_match, 'Missing RSS page title: '+url
        title = article['title'] if article else unescape(re.sub(r'<[^>]+>', '', title_match.group(1)))
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = title
        ET.SubElement(item, 'link').text = url
        ET.SubElement(item, 'guid', {'isPermaLink': 'true'}).text = url
        if article and article.get('website_published'):
            ET.SubElement(item, 'pubDate').text = rss_date(article['website_published'])
        if article:
            ET.SubElement(item, 'category').text = LABELS[article['category']]
        ET.SubElement(item, 'description').text = body
    ET.indent(feed, space='  ')
    content = ET.tostring(feed, encoding='utf-8', xml_declaration=True)+b'\n'
    assert len(content) < 10*1024*1024, 'RSS feed exceeds the submission size limit'
    (ROOT/'rss.xml').write_bytes(content)

def source_blog_name(url):
    if re.fullmatch(r'https://blog\.naver\.com/ohsunghani/[0-9]+', url):
        return '네이버 블로그'
    if re.fullmatch(r'https://ohsunghani\.tistory\.com/[0-9]+', url):
        return '티스토리 블로그'
    raise ValueError('Unexpected article source')

def structured(data):
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace('<', '\\u003c') + '</script>'

def sync_existing_article_title(text, article, updated):
    """Keep the original article body while syncing its catalog title everywhere."""
    replacements = [
        (r'<title>.*?</title>', '<title>'+escape(article['title'])+' | 오성한의원</title>'),
        (r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="'+attr(article['title'])+'">'),
        (r'<h1>.*?</h1>', '<h1>'+escape(article['title'])+'</h1>'),
    ]
    for pattern, replacement in replacements:
        text, count = re.subn(pattern, lambda match: replacement, text, count=1, flags=re.S)
        assert count == 1, 'Original article title field not found'
    def update_schema(match):
        schema = json.loads(match.group(1))
        if schema.get('@type') == 'Article':
            schema['headline'] = article['title']
            schema['dateModified'] = updated
        return structured(schema)
    return re.sub(r'<script type="application/ld\+json">(.*?)</script>', update_schema, text, flags=re.S)

def card(article, prefix='', heading='h2'):
    original_date = article.get('published_date')
    meta = f'<span class="journal-date">블로그 원문 {attr(original_date.replace("-", "."))}</span>' if original_date else ''
    return f'''<a class="journal-card" data-journal-entry data-category="{attr(article['category'])}" href="{prefix}{attr(article['slug'])}.html"><span class="journal-category">{LABELS[article['category']]}</span><{heading} class="journal-title">{escape(article['title'])}</{heading}><p class="journal-excerpt">{escape(article['excerpt'])}</p>{meta}<span class="journal-read">칼럼 읽기 {ARROW}</span></a>'''

def head(title, description, filename, schema=None):
    url = SITE + filename
    rss_link = '\n'+RSS_LINK if filename == 'health/index.html' else ''
    return f'''<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} | 오성한의원</title><meta name="description" content="{attr(description)}">
<link rel="canonical" href="{url}"><link rel="icon" href="../favicon.png" type="image/png">{rss_link}
<meta property="og:type" content="{'article' if schema and schema.get('@type') == 'Article' else 'website'}"><meta property="og:title" content="{attr(title)}"><meta property="og:description" content="{attr(description)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{SITE}og-image.png">
<link rel="stylesheet" href="../style.css?v={VERSION}"><link rel="stylesheet" href="../pages.css?v={VERSION}"><link rel="stylesheet" href="../journal.css?v={VERSION}">
{structured(schema) if schema else ''}'''

def related(article, articles):
    rest = [a for a in articles if a['slug'] != article['slug']]
    rest.sort(key=lambda a: a['category'] != article['category'])
    return '<section class="section journal-related" aria-labelledby="other-columns"><div class="section-head"><div><span class="eyebrow">KEEP READING</span><h2 class="section-title" id="other-columns">다른 건강칼럼도 읽어보세요</h2></div><a class="text-link" href="index.html">전체 칼럼 보기 '+ARROW+'</a></div><div class="journal-grid journal-related-grid">'+''.join(card(a, heading='h3') for a in rest[:3])+'</div></section>'

def article_html(article, articles, header, footer, updated):
    body = '<div class="callout journal-article-summary"><strong>이 글에서 살펴볼 내용</strong><ul>' + ''.join('<li>'+escape(t)+'</li>' for t in article['takeaways']) + '</ul></div>'
    toc = []
    for i, section in enumerate(article['sections'], 1):
        ident = f'article-section-{i}'
        body += f'<h2 id="{ident}">{escape(section["heading"])}</h2>'
        body += ''.join('<p>'+escape(p)+'</p>' for p in section.get('paragraphs', []))
        if section.get('items'):
            body += '<ul>'+''.join('<li>'+escape(item)+'</li>' for item in section['items'])+'</ul>'
        toc.append(f'<li><a href="#{ident}">{escape(section["heading"])}</a></li>')
    source_date = f' · 원문 작성일 {article["published_date"].replace("-", ".")}' if article.get('published_date') else ''
    source_name = source_blog_name(article['source_url'])
    body += f'<div class="journal-source"><span class="eyebrow">FROM OHSUNG BLOG</span><p>오성한의원 블로그 글을 바탕으로 홈페이지에서 읽기 쉽게 정리했습니다.</p><a class="text-link" href="{attr(article["source_url"])}" target="_blank" rel="noopener noreferrer">{escape(article["source_title"])} {ARROW}</a><p class="small-note">출처: 오성한의원 {source_name}{source_date}</p></div>'
    body += f'<div class="article-back"><a class="text-link" href="index.html">건강칼럼 목록으로 {ARROW}</a></div>'
    schema = {'@context':'https://schema.org','@type':'Article','headline':article['title'], 'description':article['excerpt'], 'url':SITE+'health/'+article['slug']+'.html','mainEntityOfPage':SITE+'health/'+article['slug']+'.html', 'author':{'@type':'Organization','name':'오성한의원','url':SITE}, 'publisher':{'@type':'Organization','name':'오성한의원','url':SITE},'datePublished':article.get('website_published',updated), 'dateModified':updated,'isBasedOn':{'@type':'Article','url':article['source_url'],'headline':article['source_title'],'datePublished':article.get('published_date')}}
    intro = f'<nav class="breadcrumb" aria-label="현재 위치"><a href="../index.html">홈</a><span aria-hidden="true">/</span><a href="index.html">건강정보</a><span aria-hidden="true">/</span><span>{LABELS[article["category"]]}</span></nav><div class="page-intro article-intro"><span class="eyebrow">{LABELS[article["category"]]}</span><h1>{escape(article["title"])}</h1><p class="article-meta">오성한의원 건강칼럼 · 블로그 글을 정리한 건강정보</p></div>'
    aside = '<aside class="article-aside" aria-label="칼럼 목차"><span class="eyebrow">IN THIS ARTICLE</span><h2>이 글의 내용</h2><ol class="article-toc">'+''.join(toc)+'</ol><a class="text-link" href="index.html">건강칼럼 전체 보기 '+ARROW+'</a><br><a class="text-link" href="../info.html">진료시간 · 오시는 길 '+ARROW+'</a></aside>'
    return '<!doctype html>\n<html lang="ko"><head>'+head(article['title'],article['excerpt'],'health/'+article['slug']+'.html',schema)+'</head><body>\n'+header+'<main id="main"><div class="container">'+intro+'<div class="article-layout"><article class="article-body">'+body+'</article>'+aside+'</div>'+related(article,articles)+'</div></main>'+footer+'</body></html>\n'

def build():
    data = json.loads((ROOT/'health/articles.json').read_text())
    articles = data['articles']
    validate_philosophy_sources(articles)
    updated = data['updated']
    assert len({a['slug'] for a in articles}) == len(articles), 'Duplicate article slugs'
    for article in articles:
        assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',article['slug']), 'Invalid article slug'
        assert article['category'] in LABELS, 'Invalid category'
        if article.get('source_url'):
            source_blog_name(article['source_url'])
    articles = sorted(articles,key=lambda a:a.get('published_date') or '',reverse=True)
    template = (ROOT/'health/airconditioner-shoulder.html').read_text()
    header = re.search(r'(<a class="skip-link".*?</header>)',template,re.S).group(1)
    footer = re.search(r'(<footer class="site-footer">.*?)</body>',template,re.S).group(1)
    for article in articles:
        if article.get('existing'):
            path = ROOT/'health'/f'{article["slug"]}.html'
            text = path.read_text()
            # Keep the established body and URL; sync its title and archive navigation.
            text = sync_existing_article_title(text, article, updated)
            if 'journal.css' not in text:
                text = text.replace('</head>',f'<link rel="stylesheet" href="../journal.css?v={VERSION}">\n</head>')
            else:
                text = re.sub(r'journal\.css(?:\?[^\"]*)?', 'journal.css?v='+VERSION, text)
            text = re.sub(r'<!-- JOURNAL RELATED START -->.*?<!-- JOURNAL RELATED END -->','',text,flags=re.S)
            marker = '<!-- JOURNAL RELATED START -->'+related(article,articles)+'<!-- JOURNAL RELATED END -->'
            text = text.replace('</main>',marker+'</main>')
            # The original main ends after its container; related cards need their own container.
            text = text.replace('<!-- JOURNAL RELATED START --><section','<!-- JOURNAL RELATED START --><div class="container"><section').replace('</section><!-- JOURNAL RELATED END -->','</section></div><!-- JOURNAL RELATED END -->')
            path.write_text(text)
        else:
            (ROOT/'health'/f'{article["slug"]}.html').write_text(article_html(article,articles,header,footer,updated))
    filters = '<button class="journal-filter" type="button" data-journal-filter="all" aria-pressed="true">전체</button>'
    filters += ''.join(f'<button class="journal-filter" type="button" data-journal-filter="{key}" aria-pressed="false">{label}</button>' for key,label in LABELS.items() if any(a['category']==key for a in articles))
    toolbar = f'<div class="journal-toolbar" data-journal-tools hidden><label class="journal-search">{SEARCH}<input type="search" data-journal-search placeholder="궁금한 증상이나 주제를 검색하세요" aria-label="건강칼럼 검색"></label><div class="journal-filters" aria-label="건강칼럼 분류">{filters}</div><button class="text-link" type="button" data-journal-clear>검색·분류 초기화</button></div>'
    schema = {'@context':'https://schema.org','@type':'CollectionPage','name':'오성한의원 건강칼럼','url':SITE+'health/index.html','mainEntity':{'@type':'ItemList','numberOfItems':len(articles),'itemListElement':[{'@type':'ListItem','position':i,'name':a['title'],'url':SITE+'health/'+a['slug']+'.html'} for i,a in enumerate(articles,1)]}}
    original_index = (ROOT/'health/index.html').read_text()
    blog_resources = re.search(r'(<section class="section blog-resources".*?</section>)',original_index,re.S)
    blog_resources = blog_resources.group(1) if blog_resources else ''
    intro = '<div class="page-intro"><span class="eyebrow">OHSUNG JOURNAL</span><h1>일상 가까이, 건강칼럼</h1><p>진료실에서 자주 만나는 질문부터 생활 속 건강 이야기까지.<br>오성한의원 블로그의 글을 정리해 한곳에 모았습니다.</p></div>'
    listing = toolbar+f'<div class="journal-status"><span data-journal-count role="status" aria-live="polite">전체 {len(articles)}개의 건강칼럼</span><span class="small-note">궁금한 글을 누르면 홈페이지 안에서 읽을 수 있습니다.</span></div><div class="journal-grid" data-journal-grid>'+''.join(card(a) for a in articles)+'</div><p class="journal-empty" data-journal-empty hidden>검색 결과가 없습니다. 다른 검색어나 분류를 선택해 주세요.</p>'
    page = '<!doctype html>\n<html lang="ko"><head>'+head('건강칼럼','교통사고, 침·약침, 한약·공진단과 생활건강에 관한 오성한의원의 건강칼럼을 홈페이지에서 읽어보세요.','health/index.html',schema)+'</head><body>'+header+'<main id="main"><div class="container">'+intro+'<section class="section journal-library" aria-label="전체 건강칼럼">'+listing+'</section>'+blog_resources+'</div></main>'+footer+f'<script src="../journal.js?v={VERSION}" defer></script></body></html>\n'
    (ROOT/'health/index.html').write_text(page)
    home = (ROOT/'index.html').read_text()
    blog_links = '<div class="journal-blog-links"><span>블로그 카테고리</span><a href="https://blog.naver.com/PostList.naver?blogId=ohsunghani&amp;from=postList&amp;categoryNo=25" target="_blank" rel="noopener noreferrer">진료 철학</a><a href="https://blog.naver.com/PostList.naver?blogId=ohsunghani&amp;from=postList&amp;categoryNo=16" target="_blank" rel="noopener noreferrer">교통사고 치료 이야기</a><a href="https://blog.naver.com/PostList.naver?blogId=ohsunghani&amp;from=postList&amp;categoryNo=18" target="_blank" rel="noopener noreferrer">공진단 이야기</a></div>'
    home_section = '<section class="section container" aria-labelledby="journal-title"><div class="section-head"><div><span class="eyebrow">OHSUNG JOURNAL</span><h2 class="section-title" id="journal-title">일상 가까이, 건강 이야기.</h2></div><a class="text-link" href="health/index.html">건강칼럼 전체 보기 '+ARROW+'</a></div><p class="journal-home-description">궁금했던 건강 이야기를 오성한의원 홈페이지에서 읽어보세요.</p><div class="journal-grid journal-home-grid">'+''.join(card(a,'health/','h3') for a in articles[:3])+'</div>'+blog_links+'</section>'
    home, count = re.subn(r'<section class="section container" aria-labelledby="journal-title">.*?</section>',home_section,home,flags=re.S)
    assert count == 1, 'Home article section not found'
    if 'journal.css' not in home:
        home = home.replace('</head>',f'<link rel="stylesheet" href="journal.css?v={VERSION}">\n</head>')
    else:
        home = re.sub(r'journal\.css(?:\?[^\"]*)?', 'journal.css?v='+VERSION, home)
    if 'type="application/rss+xml"' not in home:
        home = home.replace('</head>', RSS_LINK+'\n</head>')
    (ROOT/'index.html').write_text(home)
    build_search()
    print(f'Built {len(articles)} articles, archive and home previews.')

if __name__=='__main__':
    if sys.argv[1:] == ['--search-only']:
        build_search()
    else:
        assert not sys.argv[1:], 'Usage: build-health.py [--search-only]'
        build()
