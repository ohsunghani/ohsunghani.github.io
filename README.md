# 오성한의원 홈페이지

파주 봉일천 오성한의원의 GitHub Pages 정적 홈페이지입니다.

## 페이지

- `index.html`: 진료 분야, 빠른 방문 안내, 의료진 및 건강정보
- `about.html`: 의료진 소개
- `info.html`: 진료시간, 주소, 전화 및 길찾기
- `faq.html`: 기존 20개 질문과 검색·분류
- `health/`: 건강정보 목록과 칼럼

`style.css`는 공통 디자인과 홈, `pages.css`는 상세 페이지, `site.js`는 메뉴·FAQ·주소 복사를 담당합니다. 폰트는 `assets/fonts/`에서 제공하며 OFL 라이선스를 포함합니다. 별도 빌드나 패키지 설치 없이 열 수 있고, GitHub Pages는 `main` 브랜치 루트에서 자동 배포됩니다.

전화번호·주소·진료시간을 변경할 때는 각 페이지 공통 안내와 JSON-LD의 정보도 함께 수정합니다. URL을 추가하면 `sitemap.xml`에도 등록합니다.

## 건강칼럼 추가·수정

`health/articles.json`에 제목·분류·소개·원문 출처·본문 소제목을 추가한 뒤 다음 명령을 실행합니다.

```sh
python3 scripts/build-health.py
```

건강정보 목록, 홈페이지의 최신 원문 3개 미리보기, 개별 칼럼, 함께 읽을 글, 사이트맵을 함께 갱신합니다. 배포에는 생성된 HTML도 포함합니다. 별도 서버나 패키지 설치는 필요 없습니다. 원래부터 있던 `airconditioner-shoulder.html`의 본문과 주소는 유지합니다.

- `published_date`는 네이버 블로그 원문의 실제 작성일입니다. 알 수 없으면 `null`로 둡니다.
- 홈페이지에 처음 게시한 날은 `website_published`, 편집한 날은 맨 위 `updated`에 기록합니다.
- 분류: `pain`(통증·자세), `accident`(교통사고), `treatment`(치료·내원 안내), `herbal`(한약·공진단), `lifestyle`(생활건강), `philosophy`(진료 철학).
- 블로그에서 정리한 글은 원문 제목과 주소를 유지합니다. 확인되지 않은 치료효과·경력·통계를 추가하지 않습니다.

목록의 검색과 분류는 `journal.js`, 칼럼 카드와 목록 스타일은 `journal.css`에서 관리합니다.
