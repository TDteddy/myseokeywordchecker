#!/usr/bin/env python3
"""
SEO 키워드 예측 프로그램
웹페이지 URL을 입력받아 해당 페이지의 타겟 SEO 키워드를 분석합니다.
"""

import argparse
import json
import sys
from urllib.parse import urlparse

from scraper import WebScraper
from analyzer import SEOAnalyzer


def validate_url(url: str) -> str:
    """URL 유효성 검사 및 정규화"""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError("유효하지 않은 URL입니다.")

    return url


def print_banner():
    """프로그램 배너 출력"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║           SEO 키워드 예측기 (SEO Keyword Predictor)        ║
║      웹페이지를 분석하여 타겟 SEO 키워드를 예측합니다       ║
╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def analyze_url(url: str, output_json: bool = False, model: str = "gpt-4o-mini"):
    """URL을 분석하여 SEO 키워드 예측"""

    print(f"\n[1/3] URL 검증 중...")
    try:
        url = validate_url(url)
        print(f"      분석 대상: {url}")
    except ValueError as e:
        print(f"오류: {e}")
        return None

    print(f"\n[2/3] 웹페이지 스크래핑 중...")
    scraper = WebScraper()
    seo_data = scraper.extract_seo_elements(url)

    if not seo_data:
        print("오류: 웹페이지를 가져올 수 없습니다.")
        return None

    print(f"      제목: {seo_data.get('title', 'N/A')[:50]}...")
    print(f"      내부 링크: {seo_data['links']['internal_count']}개")
    print(f"      외부 링크: {seo_data['links']['external_count']}개")
    print(f"      이미지: {len(seo_data.get('images', []))}개")

    print(f"\n[3/3] GPT API로 SEO 키워드 분석 중... (모델: {model})")
    try:
        analyzer = SEOAnalyzer()

        if output_json:
            result = analyzer.analyze_keywords(seo_data, model)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            result = analyzer.get_quick_analysis(seo_data, model)
            print(result)

        return result

    except ValueError as e:
        print(f"\n오류: {e}")
        print("OPENAI_API_KEY 환경변수를 설정하거나 .env 파일을 생성해주세요.")
        return None


def interactive_mode():
    """대화형 모드"""
    print_banner()
    print("URL을 입력하면 SEO 키워드를 분석합니다. 종료하려면 'quit' 또는 'exit'를 입력하세요.\n")

    while True:
        try:
            url = input("\n분석할 URL을 입력하세요: ").strip()

            if url.lower() in ["quit", "exit", "q"]:
                print("\n프로그램을 종료합니다. 감사합니다!")
                break

            if not url:
                print("URL을 입력해주세요.")
                continue

            analyze_url(url)

        except KeyboardInterrupt:
            print("\n\n프로그램을 종료합니다.")
            break


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="웹페이지 SEO 키워드 예측기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python main.py https://example.com
  python main.py https://example.com --json
  python main.py https://example.com --model gpt-4o
  python main.py  # 대화형 모드
        """,
    )

    parser.add_argument("url", nargs="?", help="분석할 웹페이지 URL")
    parser.add_argument(
        "--json", "-j", action="store_true", help="결과를 JSON 형식으로 출력"
    )
    parser.add_argument(
        "--model",
        "-m",
        default="gpt-4o-mini",
        choices=["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        help="사용할 GPT 모델 (기본값: gpt-4o-mini)",
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="대화형 모드로 실행"
    )

    args = parser.parse_args()

    if args.interactive or not args.url:
        interactive_mode()
    else:
        print_banner()
        analyze_url(args.url, output_json=args.json, model=args.model)


if __name__ == "__main__":
    main()
