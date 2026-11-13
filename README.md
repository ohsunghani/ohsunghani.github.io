# 오성한의원 홈페이지

파주 봉일천 오성한의원의 GitHub Pages 정적 홈페이지입니다.

## 페이지

- `index.html`: 진료 분야, 빠른 방문 안내, 의료진 및 건강정보
- `about.html`: 의료진 소개
- `info.html`: 진료시간, 주소, 전화 및 길찾기
- `faq.html`: 기존 20개 질문과 검색·분류
- `health/`: 건강정보 목록과 칼럼

`style.css`는 공통 디자인과 홈, `pages.css`는 상세 페이지, `site.js`는 메뉴·FAQ·주소 복사를 담당합니다. 폰트는 `assets/fonts/`에서 제공하며 OFL 라이선스를 포함합니다. 별도 패키지 설치 없이 열 수 있고, `main`에 반영하면 GitHub Actions가 사이트맵과 RSS를 생성한 뒤 GitHub Pages에 배포합니다.

전화번호·주소·진료시간을 변경할 때는 각 페이지 공통 안내와 JSON-LD의 정보도 함께 수정합니다.

## 검색엔진 수집 설정

`sitemap.xml`과 전체 사이트 RSS인 `rss.xml`은 실제 HTML 파일을 바탕으로 생성합니다. 페이지 파일을 추가·삭제하면 다음 자동 배포에 반영됩니다. 소유확인 HTML, 404 페이지, `noindex` 페이지, 리다이렉트 페이지, 다른 페이지를 canonical로 지정한 중복 페이지는 제외합니다. 사이트맵의 `lastmod`는 해당 HTML 파일의 Git 수정일을 한국 날짜로 변환합니다.

로컬에서 검색 파일만 갱신하려면 다음 명령을 실행합니다. 이 모드는 기존 HTML 본문을 다시 생성하지 않습니다.

```sh
python3 scripts/build-health.py --search-only
```

정식 주소는 `https://ohsunghani.github.io/`입니다. Google Search Console과 네이버 서치어드바이저에도 같은 HTTPS 주소로 등록하고 `https://ohsunghani.github.io/sitemap.xml`을 제출합니다. 네이버 RSS 제출 주소는 `https://ohsunghani.github.io/rss.xml`입니다. `robots.txt`는 전체 수집을 허용하며 사이트맵 주소를 안내합니다. Google·네이버 소유확인 파일은 삭제하지 않습니다.

## 건강칼럼 추가·수정

건강칼럼의 주된 원문은 오성한의원 네이버 블로그입니다. 새 글은 네이버 원문을 우선 활용하고, 티스토리는 보조·백업 자료로 사용합니다. 원문을 고를 때는 이미 발행한 칼럼과 주제가 겹치는지 확인합니다.

발행 요청을 받으면 최신 글부터 검토하고, 2026년 이후 작성된 원문을 우선 활용합니다. 이전 연도 글은 적합한 최근 원문이 없을 때 보조적으로 검토합니다.

`philosophy`(진료 철학)는 네이버 블로그의 해당 카테고리(`categoryNo=25`, ‘오성한의원은 이렇게 진료합니다’)에 실제로 속한 원문만 사용합니다. 진료실 일화·시설 소개·다른 카테고리 글을 해석해 진료철학으로 바꾸지 않습니다. 제목뿐 아니라 원문의 주제와 취지를 유지하며, 티스토리 원문도 이 분류에는 사용하지 않습니다.

확인한 원문 목록과 제목·작성일은 `scripts/philosophy-sources.json`에 기록합니다. 새 진료철학 원문을 추가할 때는 네이버 카테고리 목록과 원문을 직접 확인한 뒤 이 목록을 갱신합니다. 전체 생성과 배포 시 검증을 통과하지 못하면 중단합니다.

`health/articles.json`에 제목·분류·소개·원문 출처·본문 소제목을 추가한 뒤 다음 명령을 실행합니다.

```sh
python3 scripts/build-health.py
```

건강정보 목록, 홈페이지의 최신 원문 3개 미리보기, 개별 칼럼, 함께 읽을 글, 사이트맵과 RSS를 함께 갱신합니다. 배포에는 생성된 HTML도 포함합니다. 별도 서버나 패키지 설치는 필요 없습니다. 원래부터 있던 `airconditioner-shoulder.html`의 본문과 주소는 유지합니다. 칼럼을 삭제할 때는 JSON 항목과 해당 HTML 파일을 함께 삭제합니다.

- `published_date`는 네이버 블로그 원문의 실제 작성일입니다. 알 수 없으면 `null`로 둡니다.
- 홈페이지에 처음 게시한 날은 `website_published`, 편집한 날은 맨 위 `updated`에 기록합니다.
- 분류: `pain`(통증·자세), `accident`(교통사고), `treatment`(치료·내원 안내), `herbal`(한약·공진단), `lifestyle`(생활건강), `philosophy`(진료 철학).
- 블로그에서 정리한 글은 원문 제목과 주소를 유지합니다. 확인되지 않은 치료효과·경력·통계를 추가하지 않습니다.

목록의 검색과 분류는 `journal.js`, 칼럼 카드와 목록 스타일은 `journal.css`에서 관리합니다.
