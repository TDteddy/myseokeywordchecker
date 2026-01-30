"""
구글 검색 순위 체커 모듈
특정 도메인이 검색어에 대해 몇 위에 노출되는지 확인합니다.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus
import time
import random
from typing import List, Dict, Optional


class GoogleRankChecker:
    """구글 검색 순위를 체크하는 클래스"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def check_rank(
        self,
        keyword: str,
        target_domain: str,
        max_results: int = 100,
        country: str = "kr"
    ) -> Dict:
        """
        특정 키워드에 대한 도메인의 구글 검색 순위를 확인합니다.

        Args:
            keyword: 검색 키워드
            target_domain: 순위를 확인할 도메인 (예: example.com)
            max_results: 최대 검색 결과 수 (기본 100)
            country: 국가 코드 (기본 kr)

        Returns:
            순위 정보 딕셔너리
        """
        # 도메인 정규화 (http://, https://, www. 제거)
        target_domain = self._normalize_domain(target_domain)

        try:
            # 구글 검색 URL 구성
            search_url = self._build_search_url(keyword, max_results, country)

            # 검색 결과 가져오기
            response = self.session.get(search_url, timeout=30)

            if response.status_code != 200:
                return {
                    "keyword": keyword,
                    "target_domain": target_domain,
                    "rank": None,
                    "found": False,
                    "error": f"검색 실패 (HTTP {response.status_code})",
                    "url": None,
                    "title": None,
                    "total_checked": 0
                }

            # HTML 파싱
            soup = BeautifulSoup(response.text, "html.parser")

            # 검색 결과 추출
            results = self._extract_search_results(soup)

            # 순위 찾기
            rank_info = self._find_domain_rank(results, target_domain)

            return {
                "keyword": keyword,
                "target_domain": target_domain,
                "rank": rank_info["rank"],
                "found": rank_info["found"],
                "url": rank_info["url"],
                "title": rank_info["title"],
                "total_checked": len(results),
                "error": None
            }

        except requests.exceptions.Timeout:
            return {
                "keyword": keyword,
                "target_domain": target_domain,
                "rank": None,
                "found": False,
                "error": "검색 타임아웃",
                "url": None,
                "title": None,
                "total_checked": 0
            }
        except Exception as e:
            return {
                "keyword": keyword,
                "target_domain": target_domain,
                "rank": None,
                "found": False,
                "error": f"오류: {str(e)}",
                "url": None,
                "title": None,
                "total_checked": 0
            }

    def check_multiple_keywords(
        self,
        keywords: List[str],
        target_domain: str,
        max_results: int = 100,
        country: str = "kr",
        delay_range: tuple = (2, 4)
    ) -> List[Dict]:
        """
        여러 키워드에 대한 순위를 확인합니다.

        Args:
            keywords: 검색 키워드 목록 (최대 10개)
            target_domain: 순위를 확인할 도메인
            max_results: 최대 검색 결과 수
            country: 국가 코드
            delay_range: 요청 간 지연 시간 범위 (초)

        Returns:
            각 키워드별 순위 정보 목록
        """
        # 최대 10개 키워드로 제한
        keywords = keywords[:10]

        results = []
        for i, keyword in enumerate(keywords):
            keyword = keyword.strip()
            if not keyword:
                continue

            result = self.check_rank(keyword, target_domain, max_results, country)
            results.append(result)

            # 마지막 키워드가 아니면 지연
            if i < len(keywords) - 1:
                delay = random.uniform(*delay_range)
                time.sleep(delay)

        return results

    def _normalize_domain(self, domain: str) -> str:
        """도메인을 정규화합니다."""
        domain = domain.lower().strip()

        # URL 형식인 경우 도메인만 추출
        if domain.startswith(("http://", "https://")):
            parsed = urlparse(domain)
            domain = parsed.netloc

        # www. 제거
        if domain.startswith("www."):
            domain = domain[4:]

        # 끝의 슬래시 제거
        domain = domain.rstrip("/")

        return domain

    def _build_search_url(self, keyword: str, num_results: int, country: str) -> str:
        """구글 검색 URL을 생성합니다."""
        encoded_keyword = quote_plus(keyword)

        # 구글 검색 URL (한국)
        url = f"https://www.google.co.kr/search?q={encoded_keyword}&num={num_results}&hl=ko&gl={country}"

        return url

    def _extract_search_results(self, soup: BeautifulSoup) -> List[Dict]:
        """HTML에서 검색 결과를 추출합니다."""
        results = []
        seen_urls = set()

        # 방법 1: div.g 셀렉터 (기존 방식)
        search_results = soup.select("div.g")

        for item in search_results:
            try:
                link_elem = item.select_one("a[href^='http']")
                if not link_elem:
                    continue

                url = link_elem.get("href", "")
                if not url or url.startswith("/search") or "google.com" in url:
                    continue

                if url in seen_urls:
                    continue
                seen_urls.add(url)

                title_elem = item.select_one("h3")
                title = title_elem.get_text(strip=True) if title_elem else ""

                results.append({
                    "url": url,
                    "title": title,
                    "description": ""
                })

            except Exception:
                continue

        # 방법 2: 결과가 없으면 다른 셀렉터 시도
        if len(results) < 5:
            # 모든 검색 결과 링크를 직접 찾기
            all_links = soup.find_all("a", href=True)

            for link in all_links:
                href = link.get("href", "")

                # 구글 내부 링크 제외
                if not href.startswith("http"):
                    continue
                if "google.com" in href or "google.co.kr" in href:
                    continue
                if "/search?" in href:
                    continue
                if href in seen_urls:
                    continue

                # 광고, 이미지 등 제외
                if "webcache.googleusercontent" in href:
                    continue
                if "/imgres?" in href:
                    continue

                seen_urls.add(href)

                # 제목 찾기 (h3가 있으면 사용)
                title = ""
                h3 = link.find("h3")
                if h3:
                    title = h3.get_text(strip=True)
                else:
                    # 링크 텍스트 사용
                    title = link.get_text(strip=True)[:100]

                if title:  # 제목이 있는 링크만 추가
                    results.append({
                        "url": href,
                        "title": title,
                        "description": ""
                    })

        return results

    def _find_domain_rank(self, results: List[Dict], target_domain: str) -> Dict:
        """검색 결과에서 타겟 도메인의 순위를 찾습니다."""
        for rank, result in enumerate(results, start=1):
            result_url = result.get("url", "")

            # URL에서 도메인 추출
            try:
                parsed = urlparse(result_url)
                result_domain = parsed.netloc.lower()

                # www. 제거
                if result_domain.startswith("www."):
                    result_domain = result_domain[4:]

                # 타겟 도메인이 결과 도메인에 포함되어 있는지 확인
                # (서브도메인도 포함)
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


def main():
    """테스트용 메인 함수"""
    checker = GoogleRankChecker()

    # 테스트
    result = checker.check_rank(
        keyword="노트북 추천",
        target_domain="coupang.com",
        max_results=50
    )

    print(f"키워드: {result['keyword']}")
    print(f"타겟 도메인: {result['target_domain']}")
    if result['found']:
        print(f"순위: {result['rank']}위")
        print(f"URL: {result['url']}")
        print(f"제목: {result['title']}")
    else:
        print(f"순위: 100위 밖 (확인된 결과: {result['total_checked']}개)")
        if result['error']:
            print(f"오류: {result['error']}")


if __name__ == "__main__":
    main()
