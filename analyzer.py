"""
GPT API를 활용한 SEO 키워드 분석 모듈
스크래핑된 데이터를 바탕으로 타겟 SEO 키워드를 예측합니다.
"""

import json
import os
from typing import Optional

from openai import OpenAI
from dotenv import load_dotenv


class SEOAnalyzer:
    """GPT API를 사용하여 SEO 키워드를 분석하는 클래스"""

    def __init__(self, api_key: Optional[str] = None):
        load_dotenv()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API 키가 필요합니다. OPENAI_API_KEY 환경변수를 설정하거나 직접 전달해주세요."
            )
        self.client = OpenAI(api_key=self.api_key)

    def analyze_keywords(self, seo_data: dict, model: str = "gpt-4o-mini") -> dict:
        """SEO 데이터를 분석하여 타겟 키워드를 예측합니다."""

        # 분석용 프롬프트 구성
        prompt = self._build_analysis_prompt(seo_data)

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": """당신은 SEO 전문가입니다. 웹페이지의 SEO 요소들을 분석하여
해당 페이지가 타겟팅하고 있는 키워드들을 예측합니다.

분석 시 고려사항:
- Title 태그의 키워드
- Meta Description의 핵심 키워드
- H1-H6 헤딩에서 반복되는 키워드
- 본문 텍스트에서 자주 등장하는 키워드
- URL 구조에 포함된 키워드
- 이미지 alt 텍스트의 키워드
- 내부/외부 링크 앵커 텍스트

결과는 반드시 JSON 형식으로 응답해주세요.""",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            return {"error": str(e), "keywords": []}

    def _build_analysis_prompt(self, seo_data: dict) -> str:
        """분석용 프롬프트를 구성합니다."""

        # 헤딩 정보 정리
        headings_text = ""
        for tag, contents in seo_data.get("headings", {}).items():
            if contents:
                headings_text += f"\n{tag.upper()}: {', '.join(contents[:10])}"

        # OG 태그 정리
        og_text = ""
        for key, value in seo_data.get("og_tags", {}).items():
            og_text += f"\n{key}: {value}"

        # 링크 앵커 텍스트 정리
        internal_anchors = [
            link["text"]
            for link in seo_data.get("links", {}).get("internal", [])
            if link.get("text")
        ][:20]
        external_anchors = [
            link["text"]
            for link in seo_data.get("links", {}).get("external", [])
            if link.get("text")
        ][:10]

        # 이미지 alt 텍스트 정리
        image_alts = [
            img["alt"] for img in seo_data.get("images", []) if img.get("alt")
        ][:15]

        prompt = f"""다음 웹페이지의 SEO 요소들을 분석하여 이 페이지가 타겟팅하고 있는 키워드들을 예측해주세요.

## 기본 정보
- URL: {seo_data.get('url', '')}
- 도메인: {seo_data.get('domain', '')}
- 경로: {seo_data.get('path', '')}

## Title
{seo_data.get('title', '없음')}

## Meta Description
{seo_data.get('meta_description', '없음')}

## Meta Keywords
{seo_data.get('meta_keywords', '없음')}

## Open Graph 태그
{og_text if og_text else '없음'}

## 헤딩 태그
{headings_text if headings_text else '없음'}

## Canonical URL
{seo_data.get('canonical', '없음')}

## 내부 링크 앵커 텍스트
{', '.join(internal_anchors) if internal_anchors else '없음'}

## 외부 링크 앵커 텍스트
{', '.join(external_anchors) if external_anchors else '없음'}

## 이미지 Alt 텍스트
{', '.join(image_alts) if image_alts else '없음'}

## 본문 텍스트 (일부)
{seo_data.get('body_text', '')[:3000]}

---

위 정보를 바탕으로 다음 JSON 형식으로 분석 결과를 제공해주세요:

{{
    "main_keywords": ["메인 타겟 키워드 3-5개"],
    "secondary_keywords": ["보조 키워드 5-10개"],
    "long_tail_keywords": ["롱테일 키워드 5-10개"],
    "topic_category": "페이지의 주제 카테고리",
    "target_audience": "추정 타겟 오디언스",
    "seo_score": {{
        "title_optimization": "상/중/하",
        "meta_description": "상/중/하",
        "heading_structure": "상/중/하",
        "content_relevance": "상/중/하",
        "overall": "상/중/하"
    }},
    "recommendations": [
        {{
            "category": "개선 항목 (예: Title, Meta Description, 헤딩 구조 등)",
            "current": "현재 상태 설명 (예: 현재 Title이 80자로 너무 김)",
            "suggestion": "개선 제안 (예: 50-60자 이내로 줄이고 핵심 키워드를 앞에 배치)",
            "priority": "높음/중간/낮음"
        }}
    ],
    "keyword_density_estimate": {{
        "키워드1": "추정 밀도 %",
        "키워드2": "추정 밀도 %"
    }},
    "competitor_keywords": ["경쟁에 활용할 수 있는 관련 키워드 제안"],
    "analysis_summary": "전체 분석 요약 (2-3문장)"
}}"""

        return prompt

    def expand_keywords(
        self, keywords: list, product_info: str = "", model: str = "gpt-4o-mini"
    ) -> dict:
        """기존 키워드를 바탕으로 새로운 키워드를 발굴합니다."""

        keywords_text = ", ".join(keywords[:20])

        prompt = f"""다음 키워드들을 바탕으로 SEO에 활용할 수 있는 새로운 키워드를 발굴해주세요.

## 기존 키워드
{keywords_text}

## 제품/서비스 정보
{product_info if product_info else '(제공되지 않음)'}

다음 JSON 형식으로 응답해주세요:

{{
    "related_keywords": ["연관 키워드 10-15개 - 기존 키워드와 의미적으로 관련된 키워드"],
    "semantic_keywords": ["시맨틱 키워드 10-15개 - LSI(Latent Semantic Indexing) 키워드"],
    "question_keywords": ["질문형 키워드 5-10개 - 사용자들이 검색할 만한 질문 형태"],
    "buyer_intent_keywords": ["구매 의도 키워드 5-10개 - 구매 전환에 효과적인 키워드"],
    "comparison_keywords": ["비교 키워드 5-10개 - vs, 비교, 차이 등이 포함된 키워드"],
    "problem_solution_keywords": ["문제-해결 키워드 5-10개 - 고객의 문제와 해결책 관련"],
    "trending_suggestions": ["트렌드 키워드 제안 5개 - 현재 트렌드에 맞는 키워드 아이디어"],
    "negative_keywords": ["제외 추천 키워드 5개 - 광고 시 제외하면 좋을 키워드"],
    "keyword_clusters": [
        {{
            "theme": "클러스터 주제",
            "keywords": ["관련 키워드 그룹"]
        }}
    ],
    "content_ideas": ["이 키워드들로 작성할 수 있는 콘텐츠 아이디어 5개"]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": """당신은 SEO 및 키워드 리서치 전문가입니다.
주어진 키워드를 분석하여 검색 엔진 최적화와 콘텐츠 마케팅에 활용할 수 있는
다양한 관련 키워드를 발굴합니다. 한국어 키워드에 집중해주세요.""",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            return {"error": str(e)}

    def find_similar_products(
        self, product_name: str, category: str = "", model: str = "gpt-4o-mini"
    ) -> dict:
        """비슷한 제품/서비스와 관련 검색어를 찾습니다."""

        prompt = f"""다음 제품/서비스와 비슷하거나 경쟁 관계에 있는 제품들과 관련 검색어를 찾아주세요.

## 제품/서비스명
{product_name}

## 카테고리
{category if category else '(자동 추정)'}

다음 JSON 형식으로 응답해주세요:

{{
    "product_category": "추정 카테고리",
    "similar_products": [
        {{
            "name": "비슷한 제품명",
            "reason": "유사한 이유",
            "search_keywords": ["이 제품 관련 검색 키워드"]
        }}
    ],
    "competitor_brands": ["경쟁 브랜드 5-10개"],
    "alternative_searches": ["대체재 검색 키워드 10개"],
    "complementary_products": ["함께 구매하는 보완재 제품 5-10개"],
    "price_range_keywords": ["가격대별 검색 키워드 - 저렴한, 프리미엄, 가성비 등"],
    "use_case_keywords": ["사용 목적별 키워드 - 업무용, 가정용, 선물용 등"],
    "target_audience_keywords": ["타겟 고객별 키워드 - 학생용, 직장인용, 초보자용 등"],
    "seasonal_keywords": ["시즌/이벤트 관련 키워드"],
    "marketplace_keywords": ["마켓플레이스별 검색 키워드 - 쿠팡, 네이버, 11번가 등"],
    "seo_recommendations": ["이 제품 SEO를 위한 추천사항 3-5개"]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": """당신은 이커머스 및 제품 마케팅 전문가입니다.
제품 분석을 통해 경쟁 제품, 대체재, 관련 검색어를 찾아내고
효과적인 SEO 및 마케팅 전략을 제안합니다. 한국 시장에 초점을 맞춰주세요.""",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            return {"error": str(e)}

    def get_quick_analysis(self, seo_data: dict, model: str = "gpt-4o-mini") -> str:
        """간단한 텍스트 형식의 분석 결과를 반환합니다."""

        result = self.analyze_keywords(seo_data, model)

        if "error" in result and result.get("error"):
            return f"분석 중 오류 발생: {result['error']}"

        output = []
        output.append("\n" + "=" * 60)
        output.append("SEO 키워드 분석 결과")
        output.append("=" * 60)

        output.append(f"\n주제 카테고리: {result.get('topic_category', 'N/A')}")
        output.append(f"타겟 오디언스: {result.get('target_audience', 'N/A')}")

        output.append("\n--- 메인 키워드 ---")
        for kw in result.get("main_keywords", []):
            output.append(f"  * {kw}")

        output.append("\n--- 보조 키워드 ---")
        for kw in result.get("secondary_keywords", []):
            output.append(f"  - {kw}")

        output.append("\n--- 롱테일 키워드 ---")
        for kw in result.get("long_tail_keywords", []):
            output.append(f"  - {kw}")

        seo_score = result.get("seo_score", {})
        if seo_score:
            output.append("\n--- SEO 점수 ---")
            output.append(f"  Title 최적화: {seo_score.get('title_optimization', 'N/A')}")
            output.append(f"  Meta Description: {seo_score.get('meta_description', 'N/A')}")
            output.append(f"  헤딩 구조: {seo_score.get('heading_structure', 'N/A')}")
            output.append(f"  콘텐츠 관련성: {seo_score.get('content_relevance', 'N/A')}")
            output.append(f"  종합 점수: {seo_score.get('overall', 'N/A')}")

        output.append("\n--- 개선 제안 ---")
        for rec in result.get("recommendations", []):
            output.append(f"  > {rec}")

        output.append("\n--- 분석 요약 ---")
        output.append(result.get("analysis_summary", ""))

        output.append("\n" + "=" * 60)

        return "\n".join(output)


def main():
    """테스트용 메인 함수"""
    # 테스트용 더미 데이터
    test_data = {
        "url": "https://example.com/products/laptop",
        "domain": "example.com",
        "path": "/products/laptop",
        "title": "최고의 노트북 추천 2024 - 가성비 노트북 비교",
        "meta_description": "2024년 최고의 노트북을 추천합니다. 가성비 좋은 노트북부터 고성능 게이밍 노트북까지 비교 분석.",
        "meta_keywords": "노트북, 노트북 추천, 가성비 노트북, 게이밍 노트북",
        "headings": {
            "h1": ["2024 노트북 추천 가이드"],
            "h2": ["가성비 노트북 TOP 5", "게이밍 노트북 추천", "업무용 노트북 비교"],
        },
        "body_text": "노트북 구매를 고민하시나요? 2024년 최신 노트북 추천 목록을 확인하세요...",
    }

    try:
        analyzer = SEOAnalyzer()
        result = analyzer.get_quick_analysis(test_data)
        print(result)
    except ValueError as e:
        print(f"오류: {e}")


if __name__ == "__main__":
    main()
