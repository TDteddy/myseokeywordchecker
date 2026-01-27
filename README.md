# SEO 키워드 예측기 (SEO Keyword Predictor)

웹페이지 URL을 입력하면 해당 페이지를 스크래핑하여 GPT API를 통해 타겟 SEO 키워드를 예측하는 프로그램입니다.

## 기능

- 웹페이지 SEO 요소 자동 추출 (Title, Meta, Headings, 본문 등)
- GPT API를 활용한 타겟 키워드 예측
- 메인/보조/롱테일 키워드 분류
- SEO 최적화 점수 평가
- 개선 제안사항 제공
- **웹 UI** 및 **CLI** 모두 지원

## 설치

```bash
# 저장소 클론
git clone <repository-url>
cd myseokeywordchecker

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

## 설정

OpenAI API 키가 필요합니다.

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일을 열어 API 키 설정
# OPENAI_API_KEY=your_openai_api_key_here
```

## 사용법

### 웹 버전 (권장)

```bash
# 웹 서버 실행
python app.py

# 브라우저에서 접속
# http://localhost:5000
```

웹 브라우저에서 URL을 입력하고 분석 버튼을 클릭하면 결과를 확인할 수 있습니다.

### CLI 버전

```bash
# URL 직접 지정
python main.py https://example.com

# 대화형 모드
python main.py

# JSON 형식으로 출력
python main.py https://example.com --json

# 다른 GPT 모델 사용
python main.py https://example.com --model gpt-4o
```

### 사용 가능한 모델

- `gpt-4o-mini` (기본값, 빠르고 저렴)
- `gpt-4o` (높은 정확도)
- `gpt-4-turbo`
- `gpt-3.5-turbo`

## 스크린샷

웹 UI에서 제공하는 기능:

- URL 입력 및 GPT 모델 선택
- 페이지 기본 정보 (제목, 링크 수, 이미지 수)
- 메인/보조/롱테일 키워드 분류
- SEO 최적화 점수 (Title, Meta, 헤딩, 콘텐츠)
- 개선 제안사항
- 분석 요약

## 프로젝트 구조

```
myseokeywordchecker/
├── app.py              # Flask 웹 서버
├── main.py             # CLI 프로그램
├── scraper.py          # 웹 스크래핑 모듈
├── analyzer.py         # GPT API 연동 분석 모듈
├── templates/
│   └── index.html      # 웹 UI 템플릿
├── requirements.txt    # 의존성 목록
├── .env.example        # 환경변수 예시
├── .gitignore          # Git 무시 파일
└── README.md           # 이 파일
```

## API 엔드포인트

### POST /analyze

URL을 분석하여 SEO 키워드를 예측합니다.

**Request:**
```json
{
    "url": "https://example.com",
    "model": "gpt-4o-mini"
}
```

**Response:**
```json
{
    "success": true,
    "url": "https://example.com",
    "scrape_info": {
        "title": "Example Domain",
        "internal_links": 5,
        "external_links": 3,
        "images": 2
    },
    "analysis": {
        "main_keywords": ["키워드1", "키워드2"],
        "secondary_keywords": ["보조1", "보조2"],
        "long_tail_keywords": ["롱테일1"],
        "topic_category": "카테고리",
        "target_audience": "타겟",
        "seo_score": {
            "title_optimization": "상",
            "meta_description": "중",
            "heading_structure": "상",
            "content_relevance": "상",
            "overall": "상"
        },
        "recommendations": ["제안1", "제안2"],
        "analysis_summary": "분석 요약"
    }
}
```

## 라이선스

MIT License
