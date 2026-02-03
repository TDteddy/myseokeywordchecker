"""
네이버 검색 순위 체커 모듈
네이버 Open API를 사용하여 검색 순위 확인
"""

import os
import requests
from urllib.parse import urlparse, quote
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class NaverRankChecker:
    """네이버 검색 순위를 체크하는 클래스"""

    API_URL = "https://openapi.naver.com/v1/search/webkr.json"

    def __init__(self, client_id: str = None, client_secret: str = None):
        """
        Args:
            client_id: 네이버 API 클라이언트 ID (없으면 환경변수에서 로드)
            client_secret: 네이버 API 클라이언트 시크릿 (없으면 환경변수에서 로드)
        """
        self.client_id = client_id or os.getenv("NAVER_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("NAVER_CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "네이버 API 키가 필요합니다. "
                "NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 환경변수를 설정하세요."
            )

        self.headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }

    def check_rank(
        self,
        keyword: str,
        target_domain: str,
        max_results: int = 100,
        debug: bool = False
    ) -> Dict:
        """
        특정 키워드에 대한 도메인의 네이버 검색 순위를 확인합니다.

        Args:
            keyword: 검색 키워드
            target_domain: 순위를 확인할 도메인 (예: example.com)
            max_results: 최대 검색 결과 수 (기본 100, 최대 1000)
            debug: 디버그 모드 (상세 정보 반환)

        Returns:
            순위 정보 딕셔너리
        """
        target_domain = self._normalize_domain(target_domain)
        all_results = []

        try:
            # 네이버 API는 한 번에 최대 100개, start 최대 1000
            # 여러 번 호출해서 max_results까지 가져옴
            display = min(100, max_results)
            start = 1

            while len(all_results) < max_results and start <= 1000:
                params = {
                    "query": keyword,
                    "display": display,
                    "start": start,
                }

                response = requests.get(
                    self.API_URL,
                    headers=self.headers,
                    params=params,
                    timeout=10
                )

                if response.status_code != 200:
                    error_msg = f"API 오류 (HTTP {response.status_code})"
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("errorMessage", error_msg)
                    except Exception:
                        pass

                    result = {
                        "keyword": keyword,
                        "target_domain": target_domain,
                        "rank": None,
                        "found": False,
                        "error": error_msg,
                        "url": None,
                        "title": None,
                        "total_checked": len(all_results)
                    }
                    if debug:
                        result["debug"] = {
                            "status_code": response.status_code,
                            "response": response.text[:500]
                        }
                    return result

                data = response.json()
                items = data.get("items", [])

                if not items:
                    break

                for item in items:
                    all_results.append({
                        "url": item.get("link", ""),
                        "title": self._clean_html(item.get("title", "")),
                        "description": self._clean_html(item.get("description", ""))
                    })

                # 더 이상 결과가 없으면 중단
                if len(items) < display:
                    break

                start += display

            # 순위 찾기
            rank_info = self._find_domain_rank(all_results, target_domain)

            result = {
                "keyword": keyword,
                "target_domain": target_domain,
                "rank": rank_info["rank"],
                "found": rank_info["found"],
                "url": rank_info["url"],
                "title": rank_info["title"],
                "total_checked": len(all_results),
                "error": None
            }

            if debug:
                result["debug"] = {
                    "total_results": data.get("total", 0),
                    "extracted_results": all_results[:10]
                }

            return result

        except requests.exceptions.Timeout:
            return {
                "keyword": keyword,
                "target_domain": target_domain,
                "rank": None,
                "found": False,
                "error": "API 타임아웃",
                "url": None,
                "title": None,
                "total_checked": len(all_results)
            }
        except Exception as e:
            return {
                "keyword": keyword,
                "target_domain": target_domain,
                "rank": None,
                "found": False,
                "error": f"오류: {str(e)[:100]}",
                "url": None,
                "title": None,
                "total_checked": len(all_results)
            }

    def check_multiple_keywords(
        self,
        keywords: List[str],
        target_domain: str,
        max_results: int = 100
    ) -> List[Dict]:
        """
        여러 키워드에 대한 순위를 확인합니다.

        Args:
            keywords: 검색 키워드 목록 (최대 10개)
            target_domain: 순위를 확인할 도메인
            max_results: 최대 검색 결과 수

        Returns:
            각 키워드별 순위 정보 목록
        """
        keywords = keywords[:10]
        results = []

        for keyword in keywords:
            keyword = keyword.strip()
            if not keyword:
                continue

            result = self.check_rank(keyword, target_domain, max_results)
            results.append(result)

        return results

    def _normalize_domain(self, domain: str) -> str:
        """도메인을 정규화합니다."""
        domain = domain.lower().strip()

        if domain.startswith(("http://", "https://")):
            parsed = urlparse(domain)
            domain = parsed.netloc

        if domain.startswith("www."):
            domain = domain[4:]

        domain = domain.rstrip("/")
        return domain

    def _clean_html(self, text: str) -> str:
        """HTML 태그를 제거합니다."""
        import re
        return re.sub(r'<[^>]+>', '', text)

    def _find_domain_rank(self, results: List[Dict], target_domain: str) -> Dict:
        """검색 결과에서 타겟 도메인의 순위를 찾습니다."""
        for rank, result in enumerate(results, start=1):
            result_url = result.get("url", "")

            try:
                parsed = urlparse(result_url)
                result_domain = parsed.netloc.lower()

                if result_domain.startswith("www."):
                    result_domain = result_domain[4:]

                # 타겟 도메인이 결과 도메인에 포함되어 있는지 확인
                if target_domain in result_domain or result_domain.endswith("." + target_domain):
                    return {
                        "found": True,
                        "rank": rank,
                        "url": result_url,
                        "title": result.get("title", "")
                    }

            except Exception:
                continue

        return {
            "found": False,
            "rank": None,
            "url": None,
            "title": None
        }


# 하위 호환성을 위한 별칭
GoogleRankChecker = NaverRankChecker


def main():
    """테스트용 메인 함수"""
    import sys

    debug_mode = "--debug" in sys.argv

    try:
        checker = NaverRankChecker()
    except ValueError as e:
        print(f"오류: {e}")
        print("\n.env 파일에 다음 내용을 추가하세요:")
        print("NAVER_CLIENT_ID=your_client_id")
        print("NAVER_CLIENT_SECRET=your_client_secret")
        return

    result = checker.check_rank(
        keyword="손목보호대",
        target_domain="aidershop.com",
        max_results=100,
        debug=debug_mode
    )

    print(f"\n키워드: {result['keyword']}")
    print(f"타겟 도메인: {result['target_domain']}")

    if result['found']:
        print(f"순위: {result['rank']}위")
        print(f"URL: {result['url']}")
        print(f"제목: {result['title']}")
    else:
        print(f"순위: {result['total_checked']}위 밖")
        if result['error']:
            print(f"오류: {result['error']}")

    if debug_mode and "debug" in result:
        print("\n=== 디버그 정보 ===")
        debug_info = result["debug"]
        print(f"총 검색 결과: {debug_info.get('total_results', 'N/A')}")

        print(f"\n추출된 결과 (상위 10개):")
        for i, r in enumerate(debug_info.get("extracted_results", []), 1):
            print(f"  {i}. {r.get('title', '')[:50]}")
            print(f"     URL: {r.get('url', '')[:70]}")


if __name__ == "__main__":
    main()
