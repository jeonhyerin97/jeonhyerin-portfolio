# JEONHYERIN 포트폴리오 웹사이트

건축 프로젝트 아카이브 포트폴리오 웹사이트입니다.

---

## 개요

- **디자인 컨셉**: 미니멀, 모던, 블랙 배경
- **참고 사이트**: [big.dk](https://big.dk/), [vcrworks.kr/prjct](https://vcrworks.kr/prjct)
- **기술 스택**: 순수 HTML, CSS, JavaScript (프레임워크 없음)

---

## 파일 구조

```
📁 프로젝트 폴더
├── index.html        # 메인 랜딩 페이지
├── projects.html     # 프로젝트 아카이브 페이지
├── drawings.html     # 드로잉 아카이브 페이지
├── about.html        # 소개 페이지
├── styles.css        # 공통 스타일시트
├── script.js         # 공통 인터랙션 스크립트
├── admin_gui.py      # 관리자 GUI 도구 (프로젝트/이미지 관리)
├── setup_github.py   # GitHub 저장소 초기 설정
├── requirements.txt  # Python 의존성
├── .gitignore        # Git 제외 파일 목록
├── README.md         # 이 문서
├── backups/          # 자동 백업 폴더
└── images/           # 이미지 폴더
    ├── projects/     # 프로젝트 이미지
    │   └── {slug}/   # 프로젝트별 폴더
    │       ├── thumb.jpg/webp      # 그리드 썸네일
    │       ├── main.jpg/webp       # 상세 페이지 메인 이미지
    │       ├── 01.jpg/webp, ...    # 서브 이미지
    │       ├── model_images/       # 모델 이미지 (3열 그리드)
    │       └── slide_images/       # 슬라이드 이미지
    └── drawings/     # 드로잉 이미지 (동일 구조)
```

---

## 페이지별 설명

### 1. index.html (메인 랜딩)
- 화면 중앙에 "JEONHYERIN" 텍스트만 표시
- 극도로 미니멀한 디자인
- 네비게이션은 마우스 호버 시에만 나타남
- 하단에 미세한 스크롤 유도 애니메이션

### 2. projects.html (프로젝트 아카이브)
- 정사각형 썸네일 이미지 그리드 형태로 표시 (vcrworks.kr/prjct 스타일)
- 3열 그리드 (데스크톱) → 2열 (태블릿) → 1열 (모바일)
- 호버 시: 이미지가 살짝 어두워지며 프로젝트 제목과 연도가 나타남
- 클릭 시 전체화면 오버레이 모달로 상세 정보 표시
- 상세 정보: 제목, 연도, 위치, 프로그램, 상태, 설명, 이미지 플레이스홀더

### 3. drawings.html (드로잉 아카이브)
- projects.html과 동일한 그리드 구조
- 드로잉/스케치 작업용 아카이브

### 4. about.html (소개)
- 이름 및 직함
- 바이오/소개글
- 학력 (EDUCATION)
- 경력 (EXPERIENCE)
- 수상/인정 (RECOGNITION)
- 연락처 (CONTACT)

---

## 주요 기능

### 그리드 썸네일 (vcrworks 스타일)
- 정사각형(1:1) 비율의 이미지 카드 그리드
- 호버 효과: 배경 어두워짐 + 제목/연도 페이드인 + 이미지 살짝 확대
- 부드러운 트랜지션 (250ms)

### 오버레이 모달
- 프로젝트/드로잉 클릭 시 전체화면 오버레이 표시
- 부드러운 페이드 + 슬라이드 업 트랜지션
- 하단 PREV/NEXT 버튼으로 이전/다음 항목 이동
- 우상단 X 버튼으로 닫기

### 키보드 접근성
| 키 | 동작 |
|---|---|
| `ESC` | 오버레이 닫기 |
| `←` (왼쪽 화살표) | 이전 프로젝트 |
| `→` (오른쪽 화살표) | 다음 프로젝트 |
| `Tab` | 오버레이 내 포커스 이동 (트랩) |

### 반응형 디자인
- 데스크톱: 넓은 여백, 큰 타이포그래피
- 모바일: 좁은 여백, 조정된 폰트 크기
- 640px 기준 브레이크포인트

### 접근성
- 시맨틱 HTML 사용
- ARIA 속성 적용 (aria-hidden, aria-modal, aria-label 등)
- 포커스 관리 (오버레이 열림/닫힘 시 포커스 복원)
- `prefers-reduced-motion` 지원 (모션 감소 설정 존중)

---

## 사용 방법

### 로컬에서 열기
1. `index.html` 파일을 브라우저에서 직접 열기
2. 또는 로컬 서버 실행:
   ```bash
   # Python 3
   python -m http.server 8000
   
   # Node.js (npx)
   npx serve
   ```
3. 브라우저에서 `http://localhost:8000` 접속

### 콘텐츠 수정 (관리자 도구)

1. 관리자 GUI 실행:
   ```bash
   python admin_gui.py
   ```

2. **프로젝트 관리**:
   - 프로젝트 추가/수정/삭제
   - 이미지 업로드 (자동 최적화 및 WebP 변환)
   - 커스텀 메타 필드 추가

3. **About 페이지 편집**:
   - 학력, 경력, 전시 정보 수정
   - 링크 삽입 기능 (`[텍스트](URL)` 마크다운 형식)

4. **저장 및 배포**:
   - `✅ 저장`: 로컬에만 저장
   - `👁 미리보기`: 브라우저에서 로컬 파일 확인
   - `🚀 저장+배포`: GitHub 푸시 → Netlify 자동 배포

5. **되돌리기**: 저장 실수 시 이전 상태로 복원 가능

#### 스타일 커스터마이징
`styles.css` 상단의 CSS 변수 수정:

```css
:root {
  --color-bg: #000000;           /* 배경색 */
  --color-text: #ffffff;         /* 텍스트 색상 */
  --color-text-muted: #666666;   /* 보조 텍스트 */
  --margin-side: clamp(1.5rem, 5vw, 4rem);  /* 좌우 여백 */
  /* ... */
}
```

---

## 디자인 시스템

### 색상
| 변수명 | 값 | 용도 |
|--------|-----|------|
| `--color-bg` | `#ffffff` | 배경 |
| `--color-text` | `#000000` | 주요 텍스트 |
| `--color-text-muted` | `#555555` | 보조 텍스트 |
| `--color-text-subtle` | `#888888` | 미세 텍스트 |
| `--color-border` | `#e0e0e0` | 구분선 |

### 타이포그래피
- 기본 폰트: Futura, Century Gothic, Avenir, sans-serif
- 프로젝트 타이틀: Archivo Bold (Google Fonts)
- 한국어: Pretendard Light (cdn.jsdelivr.net)
- 프로젝트 설명: Georgia, Times New Roman, serif

### 여백
- 좌우 여백: `clamp(1.5rem, 5vw, 4rem)` (반응형)
- 네비게이션 높이: 4rem (데스크톱), 3.5rem (모바일)

---

## 브라우저 지원

- Chrome (최신)
- Firefox (최신)
- Safari (최신)
- Edge (최신)

---

## 라이선스

이 프로젝트는 개인 포트폴리오 용도로 제작되었습니다.

---

## 제작

**JEONHYERIN**  
연세대학교 실내건축학과 학부생 / 서울

© 2026 Jeon Hyerin Architects
