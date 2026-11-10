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
