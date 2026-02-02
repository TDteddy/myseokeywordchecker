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
        country: str = "kr",
        debug: bool = False
    ) -> Dict:
        """
        특정 키워드에 대한 도메인의 구글 검색 순위를 확인합니다.

        Args:
            keyword: 검색 키워드
            target_domain: 순위를 확인할 도메인 (예: example.com)
            max_results: 최대 검색 결과 수 (기본 100)
            country: 국가 코드 (기본 kr)
            debug: 디버그 모드 (상세 정보 반환)

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
                result = {
                    "keyword": keyword,
                    "target_domain": target_domain,
                    "rank": None,
                    "found": False,
                    "error": f"검색 실패 (HTTP {response.status_code})",
                    "url": None,
                    "title": None,
                    "total_checked": 0
                }
                if debug:
                    result["debug"] = {
                        "search_url": search_url,
                        "status_code": response.status_code,
                        "response_length": len(response.text),
                    }
                return result

            # HTML 파싱
            soup = BeautifulSoup(response.text, "html.parser")

            # 검색 결과 추출
            results = self._extract_search_results(soup, debug=debug)

            # 순위 찾기
            rank_info = self._find_domain_rank(results, target_domain)

            result = {
                "keyword": keyword,
                "target_domain": target_domain,
                "rank": rank_info["rank"],
                "found": rank_info["found"],
                "url": rank_info["url"],
                "title": rank_info["title"],
                "total_checked": len(results),
                "error": None
            }

            if debug:
                # 디버그 정보 추가
                result["debug"] = {
                    "search_url": search_url,
                    "status_code": response.status_code,
                    "response_length": len(response.text),
                    "has_rso": bool(soup.select_one("#rso")),
                    "h3_count": len(soup.find_all("h3")),
                    "a_count": len(soup.find_all("a", href=True)),
                    "div_g_count": len(soup.select("div.g")),
                    "extracted_results": results[:10],  # 처음 10개 결과
                    "all_h3_classes": list(set(
                        str(h3.get("class", [])) for h3 in soup.find_all("h3")
                    ))[:10],
                }

            return result

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

    def _extract_search_results(self, soup: BeautifulSoup, debug: bool = False) -> List[Dict]:
        """HTML에서 검색 결과를 추출합니다."""
        results = []
        seen_urls = set()

        def add_result(url: str, title: str, method: str = "") -> bool:
            """결과를 추가하고 성공 여부를 반환"""
            if not url or not url.startswith("http"):
                return False
            if "google.com" in url or "google.co.kr" in url:
                return False
            if "/search?" in url or "webcache.googleusercontent" in url:
                return False
            if "/imgres?" in url:
                return False
            if url in seen_urls:
                return False

            seen_urls.add(url)
            results.append({
                "url": url,
                "title": title or "",
                "description": "",
                "_method": method if debug else ""
            })
            return True

        # 방법 1: #rso 내의 모든 링크에서 검색 결과 추출 (2024-2025 구조)
        # 구글의 새로운 구조: #rso 안에 다양한 div 구조로 결과가 배치됨
        rso = soup.select_one("#rso")
        if rso:
            # #rso 내의 외부 링크를 가진 a 태그 (span > a 포함)
            rso_links = rso.select("a[href^='http']")
            for link in rso_links:
                href = link.get("href", "")

                # 제목 찾기: 같은 컨테이너 내 h3 또는 링크 텍스트
                title = ""
                # 링크 내부의 h3
                h3_in_link = link.find("h3")
                if h3_in_link:
                    title = h3_in_link.get_text(strip=True)
                else:
                    # 형제 또는 부모 컨테이너의 h3
                    parent = link.find_parent(["div"])
                    if parent:
                        h3_sibling = parent.find("h3")
                        if h3_sibling:
                            title = h3_sibling.get_text(strip=True)

                if not title:
                    # 링크 텍스트 사용 (너무 짧거나 긴 것 제외)
                    link_text = link.get_text(strip=True)
                    if 3 < len(link_text) < 200:
                        title = link_text

                if title:
                    add_result(href, title, "rso_links")

        # 방법 2: 여러 h3 클래스 셀렉터 시도 (구글이 자주 변경함)
        if len(results) < 5:
            h3_selectors = [
                "h3.LC20lb",      # 기본 검색 결과
                "h3.DKV0Md",      # 대체 클래스
                "h3.MBeuO",       # 대체 클래스
                "h3.zBAuLc",      # 2024년 신규 클래스
                "h3.qsLff",       # 2024년 신규 클래스
                "a.zReHs h3",     # 링크 안의 h3
                "div.yuRUbf h3",  # 검색 결과 컨테이너
                "div.kb0PBd h3",  # 2024년 신규 컨테이너
            ]

            for selector in h3_selectors:
                h3_titles = soup.select(selector)
                for h3 in h3_titles:
                    try:
                        # h3의 부모 또는 형제 <a> 태그 찾기
                        parent_a = h3.find_parent("a")
                        if not parent_a:
                            # 부모 div에서 a 태그 찾기
                            parent_div = h3.find_parent("div")
                            if parent_div:
                                parent_a = parent_div.find("a", href=True)

                        if not parent_a:
                            continue

                        url = parent_a.get("href", "")
                        title = h3.get_text(strip=True)
                        add_result(url, title, f"h3_{selector}")

                    except Exception:
                        continue

        # 방법 3: div.g 셀렉터 (기존 방식)
        if len(results) < 5:
            search_results = soup.select("div.g")

            for item in search_results:
                try:
                    link_elem = item.select_one("a[href^='http']")
                    if not link_elem:
                        continue

                    url = link_elem.get("href", "")
                    title_elem = item.select_one("h3")
                    title = title_elem.get_text(strip=True) if title_elem else ""

                    add_result(url, title, "div_g")

                except Exception:
                    continue

        # 방법 4: data-ved 속성을 가진 링크 (구글 검색 결과 특성)
        if len(results) < 5:
            ved_links = soup.select("a[data-ved][href^='http']")
            for link in ved_links:
                href = link.get("href", "")
                title = ""
                h3 = link.find("h3")
                if h3:
                    title = h3.get_text(strip=True)
                else:
                    link_text = link.get_text(strip=True)
                    if 3 < len(link_text) < 200:
                        title = link_text

                if title:
                    add_result(href, title, "data_ved")

        # 방법 5: cite 태그 근처의 링크 (cite는 URL 표시 영역)
        if len(results) < 5:
            cites = soup.find_all("cite")
            for cite in cites:
                try:
                    parent = cite.find_parent(["div", "span"])
                    if parent:
                        link = parent.find_parent("a") or parent.find("a", href=True)
                        if link:
                            href = link.get("href", "")
                            # 같은 컨테이너의 h3 찾기
                            container = link.find_parent("div", recursive=True)
                            title = ""
                            if container:
                                h3 = container.find("h3")
                                if h3:
                                    title = h3.get_text(strip=True)

                            if not title:
                                title = link.get_text(strip=True)[:100]

                            if title:
                                add_result(href, title, "cite")
                except Exception:
                    continue

        # 방법 6: 결과가 여전히 부족하면 모든 외부 링크 스캔
        if len(results) < 5:
            all_links = soup.find_all("a", href=True)

            for link in all_links:
                href = link.get("href", "")

                if not href.startswith("http"):
                    continue

                title = ""
                h3 = link.find("h3")
                if h3:
                    title = h3.get_text(strip=True)
                else:
                    link_text = link.get_text(strip=True)
                    if 3 < len(link_text) < 100:
                        title = link_text

                if title:
                    add_result(href, title, "fallback")

        # 디버그 정보가 아니면 _method 필드 제거
        if not debug:
            for r in results:
                r.pop("_method", None)

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
    import sys
    import json

    checker = GoogleRankChecker()

    # 디버그 모드 확인 (--debug 플래그)
    debug_mode = "--debug" in sys.argv

    # 테스트
    result = checker.check_rank(
        keyword="노트북 추천",
        target_domain="coupang.com",
        max_results=50,
        debug=debug_mode
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

    # 디버그 정보 출력
    if debug_mode and "debug" in result:
        print("\n=== 디버그 정보 ===")
        debug_info = result["debug"]
        print(f"검색 URL: {debug_info.get('search_url', 'N/A')}")
        print(f"HTTP 상태: {debug_info.get('status_code', 'N/A')}")
        print(f"응답 길이: {debug_info.get('response_length', 0):,} bytes")
        print(f"#rso 존재: {debug_info.get('has_rso', False)}")
        print(f"h3 개수: {debug_info.get('h3_count', 0)}")
        print(f"a 태그 개수: {debug_info.get('a_count', 0)}")
        print(f"div.g 개수: {debug_info.get('div_g_count', 0)}")

        print(f"\nh3 클래스 목록:")
        for cls in debug_info.get("all_h3_classes", []):
            print(f"  {cls}")

        print(f"\n추출된 결과 (상위 10개):")
        for i, r in enumerate(debug_info.get("extracted_results", []), 1):
            print(f"  {i}. {r.get('title', '')[:50]}")
            print(f"     URL: {r.get('url', '')[:70]}")
            if r.get("_method"):
                print(f"     방법: {r.get('_method')}")


if __name__ == "__main__":
    main()
