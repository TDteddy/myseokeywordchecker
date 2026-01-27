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
    "recommendations": ["SEO 개선을 위한 제안사항 3-5개"],
    "keyword_density_estimate": {{
        "키워드1": "추정 밀도 %",
        "키워드2": "추정 밀도 %"
    }},
    "competitor_keywords": ["경쟁에 활용할 수 있는 관련 키워드 제안"],
    "analysis_summary": "전체 분석 요약 (2-3문장)"
}}"""

        return prompt

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
