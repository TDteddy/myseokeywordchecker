# SEO 키워드 예측기 (SEO Keyword Predictor)

웹페이지 URL을 입력하면 해당 페이지를 스크래핑하여 GPT API를 통해 타겟 SEO 키워드를 예측하는 프로그램입니다.

## 기능

- 웹페이지 SEO 요소 자동 추출 (Title, Meta, Headings, 본문 등)
- GPT API를 활용한 타겟 키워드 예측
- 메인/보조/롱테일 키워드 분류
- SEO 최적화 점수 평가
- 개선 제안사항 제공

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

### 기본 사용

```bash
# URL 직접 지정
python main.py https://example.com

# 대화형 모드
python main.py
```

### 옵션

```bash
# JSON 형식으로 출력
python main.py https://example.com --json

# 다른 GPT 모델 사용
python main.py https://example.com --model gpt-4o

# 대화형 모드 명시적 실행
python main.py --interactive
```

### 사용 가능한 모델

- `gpt-4o-mini` (기본값, 빠르고 저렴)
- `gpt-4o` (높은 정확도)
- `gpt-4-turbo`
- `gpt-3.5-turbo`

## 출력 예시

```
╔═══════════════════════════════════════════════════════════╗
║           SEO 키워드 예측기 (SEO Keyword Predictor)        ║
╚═══════════════════════════════════════════════════════════╝

[1/3] URL 검증 중...
      분석 대상: https://example.com

[2/3] 웹페이지 스크래핑 중...
      제목: Example Domain...
      내부 링크: 5개
      외부 링크: 3개

[3/3] GPT API로 SEO 키워드 분석 중...

============================================================
SEO 키워드 분석 결과
============================================================

주제 카테고리: 기술/IT
타겟 오디언스: 개발자, IT 전문가

--- 메인 키워드 ---
  * 키워드1
  * 키워드2
  * 키워드3

--- 보조 키워드 ---
  - 보조키워드1
  - 보조키워드2

--- SEO 점수 ---
  Title 최적화: 상
  Meta Description: 중
  헤딩 구조: 상
  콘텐츠 관련성: 상
  종합 점수: 상

--- 개선 제안 ---
  > 제안1
  > 제안2
```

## 프로젝트 구조

```
myseokeywordchecker/
├── main.py          # 메인 CLI 프로그램
├── scraper.py       # 웹 스크래핑 모듈
├── analyzer.py      # GPT API 연동 분석 모듈
├── requirements.txt # 의존성 목록
├── .env.example     # 환경변수 예시
├── .gitignore       # Git 무시 파일
└── README.md        # 이 파일
```

## 라이선스

MIT License
