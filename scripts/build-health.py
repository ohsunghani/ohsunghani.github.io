#!/usr/bin/env python3
"""Render the clinic's static article archive from health/articles.json."""
from pathlib import Path
from html import escape
from datetime import date
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://ohsunghani.github.io/'
VERSION = '20261110-journal1'
LABELS = {
    'pain': '통증 · 자세', 'accident': '교통사고',
    'treatment': '치료 · 내원 안내', 'herbal': '한약 · 공진단',
    'lifestyle': '생활건강', 'philosophy': '진료 철학',
}
ARROW = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6"/></svg>'
SEARCH = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg>'

def attr(text):
    return escape(str(text), quote=True)

def structured(data):
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace('<', '\\u003c') + '</script>'

def card(article, prefix='', heading='h2'):
    original_date = article.get('published_date')
    meta = f'<span class="journal-date">블로그 원문 {attr(original_date.replace("-", "."))}</span>' if original_date else ''
    return f'''<a class="journal-card" data-journal-entry data-category="{attr(article['category'])}" href="{prefix}{attr(article['slug'])}.html"><span class="journal-category">{LABELS[article['category']]}</span><{heading} class="journal-title">{escape(article['title'])}</{heading}><p class="journal-excerpt">{escape(article['excerpt'])}</p>{meta}<span class="journal-read">칼럼 읽기 {ARROW}</span></a>'''

def head(title, description, filename, schema=None):
    url = SITE + filename
    return f'''<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} | 오성한의원</title><meta name="description" content="{attr(description)}">
<link rel="canonical" href="{url}"><link rel="icon" href="../favicon.png" type="image/png">
<meta property="og:type" content="{'article' if schema and schema.get('@type') == 'Article' else 'website'}"><meta property="og:title" content="{attr(title)}"><meta property="og:description" content="{attr(description)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{SITE}og-image.png">
<link rel="stylesheet" href="../style.css?v=20261110-gothic3"><link rel="stylesheet" href="../pages.css?v=20261110-gothic3"><link rel="stylesheet" href="../journal.css?v={VERSION}">
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
    body += f'<div class="journal-source"><span class="eyebrow">FROM OHSUNG BLOG</span><p>오성한의원 블로그 글을 바탕으로 홈페이지에서 읽기 쉽게 정리했습니다.</p><a class="text-link" href="{attr(article["source_url"])}" target="_blank" rel="noopener noreferrer">{escape(article["source_title"])} {ARROW}</a><p class="small-note">출처: 오성한의원 네이버 블로그{source_date}</p></div>'
    body += f'<div class="article-back"><a class="text-link" href="index.html">건강칼럼 목록으로 {ARROW}</a></div>'
    schema = {'@context':'https://schema.org','@type':'Article','headline':article['title'], 'description':article['excerpt'], 'url':SITE+'health/'+article['slug']+'.html','mainEntityOfPage':SITE+'health/'+article['slug']+'.html', 'author':{'@type':'Organization','name':'오성한의원','url':SITE}, 'publisher':{'@type':'Organization','name':'오성한의원','url':SITE},'datePublished':article.get('website_published',updated), 'dateModified':updated,'isBasedOn':{'@type':'Article','url':article['source_url'],'headline':article['source_title'],'datePublished':article.get('published_date')}}
    intro = f'<nav class="breadcrumb" aria-label="현재 위치"><a href="../index.html">홈</a><span aria-hidden="true">/</span><a href="index.html">건강정보</a><span aria-hidden="true">/</span><span>{LABELS[article["category"]]}</span></nav><div class="page-intro article-intro"><span class="eyebrow">{LABELS[article["category"]]}</span><h1>{escape(article["title"])}</h1><p class="article-meta">오성한의원 건강칼럼 · 블로그 글을 정리한 건강정보</p></div>'
    aside = '<aside class="article-aside" aria-label="칼럼 목차"><span class="eyebrow">IN THIS ARTICLE</span><h2>이 글의 내용</h2><ol class="article-toc">'+''.join(toc)+'</ol><a class="text-link" href="index.html">건강칼럼 전체 보기 '+ARROW+'</a><br><a class="text-link" href="../info.html">진료시간 · 오시는 길 '+ARROW+'</a></aside>'
    return '<!doctype html>\n<html lang="ko"><head>'+head(article['title'],article['excerpt'],'health/'+article['slug']+'.html',schema)+'</head><body>\n'+header+'<main id="main"><div class="container">'+intro+'<div class="article-layout"><article class="article-body">'+body+'</article>'+aside+'</div>'+related(article,articles)+'</div></main>'+footer+'</body></html>\n'

def build():
    data = json.loads((ROOT/'health/articles.json').read_text())
    articles = data['articles']
    updated = data['updated']
    assert len({a['slug'] for a in articles}) == len(articles), 'Duplicate article slugs'
    for article in articles:
        assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',article['slug']), 'Invalid article slug'
        assert article['category'] in LABELS, 'Invalid category'
        if article.get('source_url'):
            assert article['source_url'].startswith('https://blog.naver.com/ohsunghani/'), 'Unexpected article source'
    articles = sorted(articles,key=lambda a:a.get('published_date') or '',reverse=True)
    template = (ROOT/'health/airconditioner-shoulder.html').read_text()
    header = re.search(r'(<a class="skip-link".*?</header>)',template,re.S).group(1)
    footer = re.search(r'(<footer class="site-footer">.*?)</body>',template,re.S).group(1)
    for article in articles:
        if article.get('existing'):
            path = ROOT/'health'/f'{article["slug"]}.html'
            text = path.read_text()
            # Keep the established article and its URL, adding only archive navigation.
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
    home_section = '<section class="section container" aria-labelledby="journal-title"><div class="section-head"><div><span class="eyebrow">OHSUNG JOURNAL</span><h2 class="section-title" id="journal-title">일상 가까이,<br>건강 이야기.</h2></div><a class="text-link" href="health/index.html">건강칼럼 전체 보기 '+ARROW+'</a></div><p class="journal-home-description">궁금했던 건강 이야기를 오성한의원 홈페이지에서 읽어보세요.</p><div class="journal-grid journal-home-grid">'+''.join(card(a,'health/','h3') for a in articles[:3])+'</div>'+blog_links+'</section>'
    home, count = re.subn(r'<section class="section container" aria-labelledby="journal-title">.*?</section>',home_section,home,flags=re.S)
    assert count == 1, 'Home article section not found'
    if 'journal.css' not in home:
        home = home.replace('</head>',f'<link rel="stylesheet" href="journal.css?v={VERSION}">\n</head>')
    else:
        home = re.sub(r'journal\.css(?:\?[^\"]*)?', 'journal.css?v='+VERSION, home)
    (ROOT/'index.html').write_text(home)
    ns='http://www.sitemaps.org/schemas/sitemap/0.9'
    ET.register_namespace('',ns)
    tree=ET.parse(ROOT/'sitemap.xml'); sm=tree.getroot()
    current={node.find('{'+ns+'}loc').text:node for node in sm}
    for path in ['', 'health/index.html']+['health/'+a['slug']+'.html' for a in articles]:
        url=SITE+path
        node=current.get(url)
        if node is None:
            node=ET.SubElement(sm,'{'+ns+'}url');ET.SubElement(node,'{'+ns+'}loc').text=url
        lm=node.find('{'+ns+'}lastmod')
        if lm is None:lm=ET.SubElement(node,'{'+ns+'}lastmod')
        lm.text=updated
    ET.indent(tree,space='  ');tree.write(ROOT/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    print(f'Built {len(articles)} articles, archive, home previews and sitemap.')

if __name__=='__main__':
    build()
