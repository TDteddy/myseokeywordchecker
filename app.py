#!/usr/bin/env python3
"""
SEO 키워드 예측기 - Flask 웹 서버
"""

import os
import sys
from flask import Flask, render_template, request, jsonify
from scraper import WebScraper
from analyzer import SEOAnalyzer
from trends import TrendsAnalyzer
from company_keywords import CompanyKeywordAPI
from rank_checker import NaverRankChecker
from urllib.parse import urlparse

# PyInstaller 번들 여부 확인 후 경로 설정
if getattr(sys, 'frozen', False):
    # PyInstaller로 빌드된 경우
    BASE_DIR = sys._MEIPASS
else:
    # 일반 Python 실행
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))


def validate_url(url: str) -> str:
    """URL 유효성 검사 및 정규화"""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError("유효하지 않은 URL입니다.")

    return url


@app.route("/")
def index():
    """메인 페이지"""
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    """URL 분석 API"""
    data = request.get_json()
    url = data.get("url", "").strip()
    model = data.get("model", "gpt-4o-mini")

    if not url:
        return jsonify({"success": False, "error": "URL을 입력해주세요."})

    try:
        # URL 검증
        url = validate_url(url)

        # 웹페이지 스크래핑
        scraper = WebScraper()
        seo_data = scraper.extract_seo_elements(url)

        if not seo_data:
            return jsonify({"success": False, "error": "웹페이지를 가져올 수 없습니다."})

        # 스크래핑 기본 정보
        scrape_info = {
            "title": seo_data.get("title", ""),
            "meta_description": seo_data.get("meta_description", ""),
            "internal_links": seo_data["links"]["internal_count"],
            "external_links": seo_data["links"]["external_count"],
            "images": len(seo_data.get("images", [])),
            "h1_tags": seo_data.get("headings", {}).get("h1", []),
        }

        # GPT 분석
        try:
            analyzer = SEOAnalyzer()
            analysis_result = analyzer.analyze_keywords(seo_data, model)

            return jsonify(
                {
                    "success": True,
                    "url": url,
                    "scrape_info": scrape_info,
                    "seo_data": seo_data,
                    "analysis": analysis_result,
                }
            )

        except ValueError as e:
            return jsonify(
                {
                    "success": False,
                    "error": f"API 키 오류: {str(e)}",
                    "scrape_info": scrape_info,
                }
            )

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)})
    except Exception as e:
        return jsonify({"success": False, "error": f"오류 발생: {str(e)}"})


@app.route("/expand-keywords", methods=["POST"])
def expand_keywords():
    """키워드 확장 API"""
    data = request.get_json()
    keywords = data.get("keywords", [])
    product_info = data.get("product_info", "")
    model = data.get("model", "gpt-4o-mini")

    if not keywords:
        return jsonify({"success": False, "error": "키워드를 입력해주세요."})

    try:
        analyzer = SEOAnalyzer()
        result = analyzer.expand_keywords(keywords, product_info, model)

        if "error" in result:
            return jsonify({"success": False, "error": result["error"]})

        return jsonify({"success": True, "expansion": result})

    except ValueError as e:
        return jsonify({"success": False, "error": f"API 키 오류: {str(e)}"})
    except Exception as e:
        return jsonify({"success": False, "error": f"오류 발생: {str(e)}"})


@app.route("/similar-products", methods=["POST"])
def similar_products():
    """비슷한 제품 검색 API"""
    data = request.get_json()
    product_name = data.get("product_name", "").strip()
    category = data.get("category", "")
    model = data.get("model", "gpt-4o-mini")

    if not product_name:
        return jsonify({"success": False, "error": "제품명을 입력해주세요."})

    try:
        analyzer = SEOAnalyzer()
        result = analyzer.find_similar_products(product_name, category, model)

        if "error" in result:
            return jsonify({"success": False, "error": result["error"]})

        return jsonify({"success": True, "similar": result})

    except ValueError as e:
        return jsonify({"success": False, "error": f"API 키 오류: {str(e)}"})
    except Exception as e:
        return jsonify({"success": False, "error": f"오류 발생: {str(e)}"})


@app.route("/keyword-trends", methods=["POST"])
def keyword_trends():
    """키워드 Google Trends 분석 API"""
    data = request.get_json()
    keywords = data.get("keywords", [])
    timeframe = data.get("timeframe", "today 3-m")

    if not keywords:
        return jsonify({"success": False, "error": "키워드를 입력해주세요."})

    try:
        trends_analyzer = TrendsAnalyzer()

        # 키워드가 5개 이하면 일반 비교, 초과면 배치 비교
        if len(keywords) <= 5:
            result = trends_analyzer.get_keyword_interest(keywords, timeframe)
            if "error" in result:
                return jsonify({"success": False, "error": result["error"]})
            return jsonify({"success": True, "trends": result})
        else:
            # 배치로 비교
            keywords_data = trends_analyzer.compare_keywords_batch(keywords, timeframe=timeframe)
            return jsonify({
                "success": True,
                "trends": {
                    "keywords": keywords_data,
                    "timeframe": timeframe,
                    "geo": "KR",
                }
            })

    except Exception as e:
        return jsonify({"success": False, "error": f"Google Trends 오류: {str(e)}"})


@app.route("/related-queries", methods=["POST"])
def related_queries():
    """관련 검색어 조회 API"""
    data = request.get_json()
    keyword = data.get("keyword", "").strip()

    if not keyword:
        return jsonify({"success": False, "error": "키워드를 입력해주세요."})

    try:
        trends_analyzer = TrendsAnalyzer()
        result = trends_analyzer.get_related_queries(keyword)

        if "error" in result:
            return jsonify({"success": False, "error": result["error"]})

        return jsonify({"success": True, "related": result})

    except Exception as e:
        return jsonify({"success": False, "error": f"관련 검색어 조회 오류: {str(e)}"})


@app.route("/company-keywords", methods=["POST"])
def company_keywords():
    """회사 키워드 성과 데이터 조회 API"""
    data = request.get_json()
    brand = data.get("brand")
    product_line = data.get("product_line")
    product_group = data.get("product_group")
    product_name = data.get("product_name")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    limit = data.get("limit", 30)

    try:
        api = CompanyKeywordAPI()
        result = api.get_keyword_data(
            brand=brand,
            product_line=product_line,
            product_group=product_group,
            product_name=product_name,
            start_date=start_date,
            end_date=end_date,
            naver_organic_only=True  # 네이버 오가닉만
        )

        if "error" in result:
            return jsonify({"success": False, "error": result["error"]})

        # 상위 N개만 반환
        result["keywords"] = result["keywords"][:limit]

        return jsonify({"success": True, "company_data": result})

    except Exception as e:
        return jsonify({"success": False, "error": f"회사 데이터 조회 오류: {str(e)}"})


@app.route("/company-keywords/analyze", methods=["POST"])
def analyze_company_keywords():
    """특정 키워드들의 회사 성과 데이터 분석 API"""
    data = request.get_json()
    keywords = data.get("keywords", [])
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    if not keywords:
        return jsonify({"success": False, "error": "키워드를 입력해주세요."})

    try:
        api = CompanyKeywordAPI()
        result = api.analyze_keyword_performance(
            target_keywords=keywords,
            start_date=start_date,
            end_date=end_date,
            naver_organic_only=True
        )

        if "error" in result:
            return jsonify({"success": False, "error": result["error"]})

        return jsonify({"success": True, "performance": result})

    except Exception as e:
        return jsonify({"success": False, "error": f"키워드 성과 분석 오류: {str(e)}"})


@app.route("/comprehensive-recommendations", methods=["POST"])
def comprehensive_recommendations():
    """종합 개선제안 API"""
    data = request.get_json()
    seo_data = data.get("seo_data", {})
    analysis_result = data.get("analysis_result", {})
    keyword_expansion = data.get("keyword_expansion", {})
    similar_products = data.get("similar_products", {})
    trends_data = data.get("trends_data", {})
    company_keywords = data.get("company_keywords", {})
    model = data.get("model", "gpt-4o")

    if not seo_data or not analysis_result:
        return jsonify({"success": False, "error": "분석 데이터가 필요합니다."})

    try:
        analyzer = SEOAnalyzer()
        result = analyzer.generate_comprehensive_recommendations(
            seo_data=seo_data,
            analysis_result=analysis_result,
            keyword_expansion=keyword_expansion,
            similar_products=similar_products,
            trends_data=trends_data,
            company_keywords=company_keywords,
            model=model,
        )

        if "error" in result:
            return jsonify({"success": False, "error": result["error"]})

        return jsonify({"success": True, "recommendations": result})

    except ValueError as e:
        return jsonify({"success": False, "error": f"API 키 오류: {str(e)}"})
    except Exception as e:
        return jsonify({"success": False, "error": f"오류 발생: {str(e)}"})


@app.route("/rank-checker")
def rank_checker_page():
    """네이버 순위 체커 페이지"""
    return render_template("rank_checker.html")


@app.route("/check-rank", methods=["POST"])
def check_rank():
    """네이버 검색 순위 확인 API"""
    data = request.get_json()
    keyword = data.get("keyword", "").strip()
    target_domain = data.get("target_domain", "").strip()
    max_results = data.get("max_results", 100)
    debug = data.get("debug", False)

    if not keyword:
        return jsonify({"success": False, "error": "검색 키워드를 입력해주세요."})

    if not target_domain:
        return jsonify({"success": False, "error": "타겟 도메인을 입력해주세요."})

    try:
        checker = NaverRankChecker()
        result = checker.check_rank(
            keyword=keyword,
            target_domain=target_domain,
            max_results=max_results,
            debug=debug
        )

        return jsonify({"success": True, "result": result})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)})
    except Exception as e:
        return jsonify({"success": False, "error": f"순위 확인 오류: {str(e)}"})


@app.route("/check-rank-bulk", methods=["POST"])
def check_rank_bulk():
    """여러 키워드 순위 일괄 확인 API"""
    data = request.get_json()
    keywords = data.get("keywords", [])
    target_domain = data.get("target_domain", "").strip()
    max_results = data.get("max_results", 100)

    if not keywords:
        return jsonify({"success": False, "error": "검색 키워드를 입력해주세요."})

    if not target_domain:
        return jsonify({"success": False, "error": "타겟 도메인을 입력해주세요."})

    # 최대 10개로 제한
    keywords = [k.strip() for k in keywords if k.strip()][:10]

    try:
        checker = NaverRankChecker()
        results = checker.check_multiple_keywords(
            keywords=keywords,
            target_domain=target_domain,
            max_results=max_results
        )

        return jsonify({"success": True, "results": results})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)})
    except Exception as e:
        return jsonify({"success": False, "error": f"순위 확인 오류: {str(e)}"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
