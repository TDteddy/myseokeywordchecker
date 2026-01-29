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

⛔ 반드시 제외해야 할 키워드 (SEO 타겟 키워드가 아님):
- 결제/금융 조건: 무이자할부, 카드결제, 계좌이체, 대금지급조건, 할부, 결제방법, 페이코, 카카오페이, 네이버페이 등
- 배송/물류 조건: 무료배송, 당일배송, 로켓배송, 새벽배송, 택배, 배송비, 출고 등 (단, Meta Description CTA로는 활용 가능)
- 정책/약관: 반품, 교환, 환불, 취소, A/S, 보증기간, 이용약관, 개인정보 등
- 쇼핑몰 공통 UI: 장바구니, 구매하기, 찜하기, 위시리스트, 로그인, 회원가입, 마이페이지 등
- 일반적 상업 문구: 특가, 세일, 할인, 품절, 재입고, 한정수량, 이벤트 (제품과 직접 관련 없는 경우)
- 고객 서비스: 고객센터, 1:1문의, FAQ, 공지사항, 상담 등

✅ 추출해야 할 키워드:
- 제품/서비스 고유의 특성, 기능, 용도
- 브랜드명, 모델명, 제품명
- 타겟 고객층 관련 키워드
- 제품 카테고리 및 분류
- 사용자가 실제로 검색할 만한 키워드

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
다양한 관련 키워드를 발굴합니다. 한국어 키워드에 집중해주세요.

⛔ 절대 포함하지 말 것 (SEO 키워드가 아닌 상업적 조건):
- 결제: 무이자할부, 카드결제, 계좌이체, 할부, 결제방법, 간편결제 등
- 배송: 무료배송, 당일배송, 로켓배송, 택배비, 배송비 등
- 정책: 반품, 교환, 환불, 취소, A/S, 보증 등
- UI요소: 장바구니, 구매하기, 찜하기, 로그인 등
- 프로모션: 특가, 세일, 할인율, 쿠폰, 적립금 등 (제품 무관한 경우)

✅ 집중해야 할 것:
- 제품/서비스의 본질적 특성과 기능
- 사용자가 실제 검색하는 키워드
- 구매 의도가 담긴 검색어 (제품명+추천, 제품명+비교 등)""",
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
효과적인 SEO 및 마케팅 전략을 제안합니다. 한국 시장에 초점을 맞춰주세요.

⛔ 제외할 것: 결제조건(할부, 카드결제), 배송조건, 반품/교환 정책, 쇼핑몰 UI 요소는 SEO 키워드가 아닙니다.
✅ 집중할 것: 제품의 본질적 특성, 용도, 타겟 고객, 경쟁 제품명 등 실제 검색되는 키워드""",
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

    def generate_comprehensive_recommendations(
        self,
        seo_data: dict,
        analysis_result: dict,
        keyword_expansion: dict,
        similar_products: dict,
        trends_data: dict = None,
        model: str = "gpt-4o",
    ) -> dict:
        """모든 분석 결과를 종합하여 바로 사용 가능한 개선 제안을 생성합니다."""

        if trends_data is None:
            trends_data = {}

        # 현재 HTML 태그들 정리
        current_title = seo_data.get("title", "")
        current_meta = seo_data.get("meta_description", "")
        current_h1 = seo_data.get("headings", {}).get("h1", [])
        current_h2 = seo_data.get("headings", {}).get("h2", [])
        body_text = seo_data.get("body_text", "")[:2000]

        # 키워드 정보 정리
        main_keywords = analysis_result.get("main_keywords", [])
        secondary_keywords = analysis_result.get("secondary_keywords", [])
        longtail_keywords = analysis_result.get("long_tail_keywords", [])
        expanded_keywords = keyword_expansion.get("related_keywords", [])[:10]
        buyer_keywords = keyword_expansion.get("buyer_intent_keywords", [])[:5]
        question_keywords = keyword_expansion.get("question_keywords", [])[:5]
        semantic_keywords = keyword_expansion.get("semantic_keywords", [])[:10]

        # 경쟁 제품 정보
        competitor_brands = similar_products.get("competitor_brands", [])[:5]
        alternative_searches = similar_products.get("alternative_searches", [])[:5]
        similar_products_list = similar_products.get("similar_products", [])[:3]

        # 네이버 데이터랩 정보 정리
        trends_keywords = trends_data.get("keywords", [])
        trends_info = ""
        if trends_keywords:
            trends_info = "\n## 네이버 데이터랩 인기도 (점수 높을수록 검색량 많음)\n"
            for kw in trends_keywords[:10]:
                trends_info += f"- {kw.get('keyword', '')}: {kw.get('score', 0)}점 (트렌드: {kw.get('trend', 'N/A')})\n"

        prompt = f"""당신은 SEO 전문가입니다. 아래 정보를 분석하고, 사용자가 **복사해서 바로 붙여넣기만 하면 되는** 완성된 SEO 콘텐츠를 작성해주세요.

⚠️ 중요: 모든 제안은 "~하세요", "~추천합니다" 같은 조언이 아니라, **실제로 사용할 완성된 텍스트**를 제공해야 합니다.

---

## 현재 페이지 정보
- URL: {seo_data.get('url', '')}
- 현재 Title: {current_title}
- 현재 Meta Description: {current_meta if current_meta else '(없음)'}
- 현재 H1: {current_h1[0] if current_h1 else '(없음)'}
- 현재 H2들: {', '.join(current_h2[:5]) if current_h2 else '(없음)'}

## 본문 내용 일부
{body_text}

## 분석된 키워드
- 메인 키워드: {', '.join(main_keywords)}
- 보조 키워드: {', '.join(secondary_keywords[:10])}
- 롱테일 키워드: {', '.join(longtail_keywords[:10])}

## 확장 키워드
- 연관 키워드: {', '.join(expanded_keywords)}
- 시맨틱 키워드: {', '.join(semantic_keywords)}
- 구매 의도 키워드: {', '.join(buyer_keywords)}
- 질문형 키워드: {', '.join(question_keywords)}

## 경쟁 정보
- 경쟁 브랜드: {', '.join(competitor_brands)}
- 대체 검색어: {', '.join(alternative_searches)}
- 유사 제품: {', '.join([p.get('name', '') for p in similar_products_list]) if similar_products_list else '(없음)'}
{trends_info}
---

다음 JSON 형식으로 **바로 사용 가능한 완성된 콘텐츠**를 제공해주세요:

{{
    "recommendations": [
        {{
            "category": "Title 태그",
            "priority": "높음",
            "current_html": "<title>{current_title}</title>",
            "recommended_html": "<title>여기에 50-60자 이내의 최적화된 완성된 타이틀을 작성. 핵심 키워드를 앞에 배치하고, 브랜드명이나 | 구분자 활용</title>",
            "keywords_used": ["이 Title에 포함한 키워드 목록"],
            "keyword_rationale": "왜 이 키워드들을 선택했는지 설명 (검색량, 구매의도, 경쟁 키워드 고려 등)",
            "reason": "변경이 필요한 구체적인 이유",
            "expected_effect": "CTR 증가, 검색 순위 향상 등 예상 효과"
        }},
        {{
            "category": "Meta Description",
            "priority": "높음",
            "current_html": "<meta name=\\"description\\" content=\\"{current_meta if current_meta else ''}\\">",
            "recommended_html": "<meta name=\\"description\\" content=\\"여기에 150-160자 이내의 완성된 메타 설명 작성. 핵심 키워드 포함, 행동 유도 문구(CTA) 포함, 사용자가 클릭하고 싶게 만드는 매력적인 설명\\">",
            "keywords_used": ["이 Meta에 포함한 키워드 목록"],
            "keyword_rationale": "왜 이 키워드들을 선택했는지 (롱테일, 구매의도, 시맨틱 키워드 활용 등)",
            "reason": "변경 이유",
            "expected_effect": "예상 효과"
        }},
        {{
            "category": "H1 태그",
            "priority": "높음",
            "current_html": "<h1>{current_h1[0] if current_h1 else ''}</h1>",
            "recommended_html": "<h1>완성된 H1 제목 - 페이지의 핵심 주제를 명확히 전달</h1>",
            "keywords_used": ["이 H1에 포함한 키워드 목록"],
            "keyword_rationale": "키워드 선택 근거",
            "reason": "변경 이유",
            "expected_effect": "예상 효과"
        }},
        {{
            "category": "H2 섹션 구조",
            "priority": "중간",
            "current_html": "현재 H2 구조: {', '.join(current_h2[:3]) if current_h2 else '없음'}",
            "recommended_html": "<h2>추천 섹션 1: 제품/서비스 소개</h2>\\n<h2>추천 섹션 2: 주요 특징 및 장점</h2>\\n<h2>추천 섹션 3: 사용 방법/활용 팁</h2>\\n<h2>추천 섹션 4: 자주 묻는 질문 (FAQ)</h2>\\n<h2>추천 섹션 5: 관련 제품/서비스</h2>",
            "reason": "변경 이유",
            "expected_effect": "예상 효과"
        }},
        {{
            "category": "Open Graph 태그",
            "priority": "중간",
            "current_html": "(현재 OG 태그 상태)",
            "recommended_html": "<meta property=\\"og:title\\" content=\\"완성된 OG 타이틀\\">\\n<meta property=\\"og:description\\" content=\\"완성된 OG 설명 - 소셜 공유 시 표시될 매력적인 설명\\">\\n<meta property=\\"og:type\\" content=\\"product 또는 article\\">",
            "reason": "소셜 미디어 공유 최적화",
            "expected_effect": "소셜 공유 시 클릭률 향상"
        }},
        {{
            "category": "Schema Markup (구조화 데이터)",
            "priority": "중간",
            "current_html": "(현재 없음 또는 있음)",
            "recommended_html": "<script type=\\"application/ld+json\\">\\n{{\\n  \\"@context\\": \\"https://schema.org\\",\\n  \\"@type\\": \\"Product\\" 또는 \\"Article\\",\\n  \\"name\\": \\"제품/페이지명\\",\\n  \\"description\\": \\"설명\\",\\n  \\"brand\\": \\"브랜드명\\"\\n}}\\n</script>",
            "reason": "구조화 데이터 추가 이유",
            "expected_effect": "리치 스니펫 표시, 검색 결과 노출 개선"
        }}
    ],
    "keyword_selection_analysis": {{
        "selected_main_keyword": "최종 선택한 메인 키워드 1개",
        "selection_reason": "이 메인 키워드를 선택한 이유 (검색의도, 페이지 내용 적합성, 경쟁 키워드 분석 결과 등)",
        "trends_consideration": {{
            "high_score_keywords": ["트렌드 점수가 높아 우선 선택한 키워드들"],
            "rising_trend_keywords": ["상승 트렌드여서 활용한 키워드들"],
            "excluded_by_trends": ["트렌드 점수가 낮거나 하락세여서 제외한 키워드들"],
            "trends_impact_summary": "네이버 데이터랩 데이터가 키워드 선택에 미친 영향 설명"
        }},
        "from_original_keywords": ["원본 분석에서 채택한 키워드들"],
        "from_expanded_keywords": ["키워드 확장에서 채택한 키워드들"],
        "from_buyer_intent": ["구매 의도 키워드에서 채택한 것들"],
        "from_competitor_analysis": ["경쟁 제품 분석에서 채택한 키워드들"],
        "rejected_keywords": [
            {{
                "keyword": "채택하지 않은 키워드",
                "reason": "제외 이유 (너무 경쟁 치열, 검색의도 불일치, 글자수 제한, 트렌드 점수 낮음 등)"
            }}
        ],
        "keyword_placement_strategy": "키워드 배치 전략 설명 (어디에 어떤 키워드를 왜 배치했는지, 트렌드 점수 기반 배치 포함)"
    }},
    "keyword_strategy": {{
        "primary_focus": ["이 페이지에서 반드시 타겟해야 할 핵심 키워드 3-5개"],
        "secondary_targets": ["추가로 노릴 수 있는 2차 키워드 5-10개"],
        "content_gaps": ["현재 페이지에 없지만 추가하면 좋을 키워드/주제들"]
    }},
    "content_recommendations": [
        "구체적인 콘텐츠 개선 제안 1 - 어떤 내용을 어디에 추가할지",
        "구체적인 콘텐츠 개선 제안 2",
        "구체적인 콘텐츠 개선 제안 3"
    ],
    "alt_text_suggestions": [
        {{
            "image_description": "어떤 이미지인지 설명",
            "recommended_alt": "완성된 alt 텍스트 - 키워드 포함"
        }}
    ],
    "internal_link_suggestions": [
        "추가하면 좋을 내부 링크 앵커 텍스트와 연결 페이지 제안"
    ],
    "faq_content": [
        {{
            "question": "사용자들이 많이 검색하는 질문 (키워드 기반)",
            "answer": "완성된 답변 - 바로 페이지에 추가할 수 있는 형태"
        }},
        {{
            "question": "두 번째 FAQ 질문",
            "answer": "완성된 답변"
        }},
        {{
            "question": "세 번째 FAQ 질문",
            "answer": "완성된 답변"
        }}
    ],
    "competitive_strategy": {{
        "differentiation": "경쟁사 대비 이 페이지만의 차별화 포인트와 강조 방법",
        "keywords_to_target": ["경쟁사를 이기기 위해 타겟해야 할 키워드"]
    }},
    "quick_wins": [
        "지금 바로 5분 안에 적용 가능한 개선사항 1",
        "지금 바로 적용 가능한 개선사항 2",
        "지금 바로 적용 가능한 개선사항 3"
    ],
    "overall_summary": "전체 SEO 개선 전략을 2-3문장으로 요약. 가장 중요한 것부터 우선순위 설명."
}}"""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": """당신은 10년 경력의 SEO 전문가이자 카피라이터입니다.

당신의 역할은 사용자가 **복사해서 바로 붙여넣기만 하면 되는** 완성된 SEO 콘텐츠를 제공하는 것입니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📏 반드시 지켜야 할 글자 수 제한
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Title 태그: 50-60자 (한글 기준, 구글 SERP에서 잘리지 않는 길이)
• Meta Description: 150-160자 (한글 기준, 모바일에서 잘리지 않는 길이)
• H1 태그: 20-70자 (핵심 주제를 명확히 전달)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 키워드 배치 전략 (검색 노출 최적화)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 핵심 키워드는 반드시 앞쪽에 배치 (Front-loading)
  - Title: 첫 25자 이내에 메인 키워드 배치
  - Meta: 첫 70자 이내에 메인 키워드 배치
  - H1: 시작 부분에 핵심 키워드 배치
• 키워드 자연스럽게 녹이기 (키워드 스터핑 금지)
• 롱테일 키워드와 관련 키워드 조합

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🖱️ 클릭률(CTR) 향상 기법
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Title에 활용:
• 숫자 사용: "TOP 10", "5가지 방법", "2024년"
• 파워 워드: "완벽한", "최고의", "필수", "추천", "비교"
• 브래킷/괄호: [가이드], (무료배송), 【추천】
• 구분자 활용: | - :

Meta Description에 활용:
• 행동 유도(CTA): "지금 확인하세요", "바로 구매", "무료 상담"
• 혜택 강조: "무료배송", "최대 50% 할인", "당일발송"
• 긴급성: "한정 수량", "오늘만", "선착순"
• 질문형: "~를 찾고 계신가요?", "~가 고민이신가요?"
• 신뢰 요소: "전문가 추천", "베스트셀러", "리뷰 1000+"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 검색 의도(Search Intent) 매칭
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 정보 탐색(Informational): "~란?", "~방법", "~가이드"
• 구매 의도(Transactional): "~구매", "~가격", "~추천"
• 비교 검색(Commercial): "~vs~", "~비교", "~순위"
• 탐색(Navigational): 브랜드명 + 제품

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 네이버 데이터랩 데이터 활용
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 네이버 데이터랩 데이터가 제공되면, 실제 검색 인기도를 기반으로 키워드 선택
• 점수가 높은 키워드를 우선적으로 Title과 H1에 배치
• 상승 트렌드인 키워드는 적극 활용
• 하락 트렌드인 키워드는 보조 키워드로 활용하거나 제외 고려
• keyword_selection_analysis에서 트렌드 데이터를 근거로 명시

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⛔ SEO 키워드로 사용하면 안 되는 것들
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
아래는 웹페이지에 있더라도 SEO 타겟 키워드가 아닌 상업적 조건들입니다.
Title, H1, 메인 키워드에 절대 사용하지 마세요:

• 결제 관련: 무이자할부, 카드결제, 계좌이체, 대금지급조건, 할부, 결제방법, 간편결제, 페이코, 카카오페이, 네이버페이
• 배송 관련: 무료배송, 당일배송, 로켓배송, 새벽배송, 택배, 배송비, 출고일 (※ Meta Description CTA로만 활용 가능)
• 정책 관련: 반품, 교환, 환불, 취소, A/S, 보증기간, 품질보증, 이용약관
• UI 요소: 장바구니, 구매하기, 찜하기, 위시리스트, 로그인, 회원가입, 마이페이지
• 프로모션: 특가, 세일, 할인, 품절, 재입고, 한정수량, 이벤트, 쿠폰, 적립금 (제품과 직접 관련 없는 경우)
• 고객 서비스: 고객센터, 1:1문의, FAQ, 공지사항, 상담

✅ SEO 키워드로 사용해야 할 것:
• 제품/서비스의 본질적 특성, 기능, 용도
• 브랜드명, 모델명, 제품명
• 사용자가 검색엔진에 실제로 입력하는 검색어
• 구매 의도 키워드: "제품명 추천", "제품명 비교", "제품명 가격"

🚫 하지 마세요:
- "~하는 것이 좋습니다" 같은 조언
- "핵심 키워드를 포함하세요" 같은 지시
- "[여기에 입력]" 같은 플레이스홀더
- 추상적인 제안

✅ 해야 할 것:
- 실제로 사용할 수 있는 완성된 Title 태그 내용
- 바로 복사할 수 있는 Meta Description 전문
- 완성된 H1, H2 제목들
- 실제 FAQ 질문과 답변
- 구체적인 alt 텍스트

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 올바른 작성 예시
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Title 태그 예시]
❌ 나쁜 예: "<title>핵심 키워드를 앞에 배치한 타이틀을 작성하세요</title>"
❌ 나쁜 예: "<title>무드등 - 좋은 제품</title>" (너무 짧고 키워드 부족)
✅ 좋은 예: "<title>LED 무드등 추천 TOP 10 - 감성 인테리어 조명 | 무료배송</title>"
✅ 좋은 예: "<title>아이폰 15 케이스 비교 - 투명/가죽/실리콘 【2024 인기순위】</title>"

[Meta Description 예시]
❌ 나쁜 예: "좋은 제품입니다. 구매하세요."
✅ 좋은 예: "감성 인테리어의 필수템! LED 무드등 인기 TOP 10을 가격대별로 비교했습니다. 충전식/무선/리모컨 기능까지. 지금 최대 30% 할인 중. 무료배송으로 내일 바로 받아보세요."

[H1 태그 예시]
❌ 나쁜 예: "<h1>제품</h1>"
✅ 좋은 예: "<h1>2024 LED 무드등 추천 - 가성비 TOP 10 비교</h1>"

모든 콘텐츠는 한국어로 작성하고, HTML 문법은 정확하게 작성해주세요.""",
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
