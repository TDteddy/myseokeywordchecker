#!/usr/bin/env python3
"""
SEO 키워드 예측기 - Flask 웹 서버
"""

from flask import Flask, render_template, request, jsonify
from scraper import WebScraper
from analyzer import SEOAnalyzer
from urllib.parse import urlparse

app = Flask(__name__)


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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
