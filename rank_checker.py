"""
구글 검색 순위 체커 모듈
Selenium + ChromeDriver를 사용하여 구글 검색 순위 확인
"""

import time
import random
from typing import List, Dict, Optional
from urllib.parse import urlparse, quote_plus
from bs4 import BeautifulSoup

# Selenium 관련 import
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Warning: selenium not installed. Run: pip install selenium webdriver-manager")


class GoogleRankChecker:
    """구글 검색 순위를 체크하는 클래스 (Selenium 버전)"""

    def __init__(self, headless: bool = True):
        """
        Args:
            headless: 헤드리스 모드 사용 여부 (기본 True)
        """
        self.headless = headless
        self.driver = None
        self.last_request_time = 0
        self.min_delay = 3  # 최소 요청 간격 (초)

    def _init_driver(self):
        """Chrome 드라이버 초기화"""
        if not SELENIUM_AVAILABLE:
            raise ImportError("selenium이 설치되지 않았습니다. pip install selenium webdriver-manager")

        if self.driver is not None:
            return

        options = Options()

        if self.headless:
            options.add_argument('--headless=new')

        # 기본 옵션
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--lang=ko-KR')

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(30)
        except Exception as e:
            raise RuntimeError(f"Chrome 드라이버 초기화 실패: {str(e)}")

    def _close_driver(self):
        """드라이버 종료"""
        if self.driver:
            try:
                self.driver.close()
            except Exception:
                pass
            try:
                self.driver.quit()
            except Exception:
                pass
            try:
                self.driver = None
            except Exception:
                pass

    def _wait_between_requests(self):
        """요청 간 적절한 딜레이 적용"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_delay:
            delay = self.min_delay - elapsed + random.uniform(1, 3)
            time.sleep(delay)
        self.last_request_time = time.time()

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
        # 도메인 정규화
        target_domain = self._normalize_domain(target_domain)

        # 이전 드라이버가 있으면 정리
        self._close_driver()

        try:
            # 드라이버 초기화
            self._init_driver()

            # 요청 전 딜레이
            self._wait_between_requests()

            # 구글 검색 URL
            search_url = self._build_search_url(keyword, max_results, country)

            # 먼저 구글 메인 페이지 방문 (쿠키/세션 초기화)
            self.driver.get("https://www.google.co.kr")
            time.sleep(random.uniform(1, 2))

            # 쿠키 동의 버튼 클릭 시도 (있는 경우)
            try:
                cookie_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                    "button[id*='accept'], button[id*='agree'], button[jsname='b3VHJd']")
                for btn in cookie_buttons:
                    try:
                        btn.click()
                        time.sleep(0.5)
                        break
                    except Exception:
                        pass
            except Exception:
                pass

            # 검색 페이지로 이동
            self.driver.get(search_url)

            # 검색 결과 로딩 대기 (#rso 또는 #search 요소)
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#rso, #search, div.g"))
                )
            except TimeoutException:
                pass  # 타임아웃이어도 계속 진행

            # 추가 대기 (JavaScript 렌더링)
            time.sleep(random.uniform(1, 2))

            # 스크롤 다운 (더 많은 결과 로드)
            self._scroll_page()

            # 페이지 소스와 제목 가져오기 (드라이버 종료 전에)
            page_source = self.driver.page_source
            page_title = self.driver.title

            # BeautifulSoup으로 파싱
            soup = BeautifulSoup(page_source, "html.parser")

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
                result["debug"] = {
                    "search_url": search_url,
                    "page_title": page_title,
                    "response_length": len(page_source),
                    "has_rso": bool(soup.select_one("#rso")),
                    "h3_count": len(soup.find_all("h3")),
                    "a_count": len(soup.find_all("a", href=True)),
                    "div_g_count": len(soup.select("div.g")),
                    "extracted_results": results[:10],
                    "all_h3_classes": list(set(
                        str(h3.get("class", [])) for h3 in soup.find_all("h3")
                    ))[:10],
                }

            return result

        except TimeoutException:
            return {
                "keyword": keyword,
                "target_domain": target_domain,
                "rank": None,
                "found": False,
                "error": "페이지 로딩 타임아웃",
                "url": None,
                "title": None,
                "total_checked": 0
            }
        except WebDriverException as e:
            return {
                "keyword": keyword,
                "target_domain": target_domain,
                "rank": None,
                "found": False,
                "error": f"브라우저 오류: {str(e)[:100]}",
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
                "error": f"오류: {str(e)[:100]}",
                "url": None,
                "title": None,
                "total_checked": 0
            }
        finally:
            # 항상 드라이버 종료
            self._close_driver()

    def _scroll_page(self):
        """페이지 스크롤 (더 많은 결과 로드)"""
        try:
            # 부드러운 스크롤
            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(random.uniform(0.3, 0.7))

            # 맨 위로 돌아가기
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
        except Exception:
            pass

    def check_multiple_keywords(
        self,
        keywords: List[str],
        target_domain: str,
        max_results: int = 100,
        country: str = "kr",
        delay_range: tuple = (5, 10)
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
        keywords = keywords[:10]
        results = []

        try:
            for i, keyword in enumerate(keywords):
                keyword = keyword.strip()
                if not keyword:
                    continue

                result = self.check_rank(keyword, target_domain, max_results, country)
                results.append(result)

                # 마지막이 아니면 딜레이
                if i < len(keywords) - 1:
                    delay = random.uniform(*delay_range)
                    time.sleep(delay)

        finally:
            # 완료 후 드라이버 종료
            self._close_driver()

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

    def _build_search_url(self, keyword: str, num_results: int, country: str) -> str:
        """구글 검색 URL을 생성합니다."""
        encoded_keyword = quote_plus(keyword)
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

        # 방법 1: #rso 내의 모든 링크
        rso = soup.select_one("#rso")
        if rso:
            rso_links = rso.select("a[href^='http']")
            for link in rso_links:
                href = link.get("href", "")
                title = ""

                h3_in_link = link.find("h3")
                if h3_in_link:
                    title = h3_in_link.get_text(strip=True)
                else:
                    parent = link.find_parent(["div"])
                    if parent:
                        h3_sibling = parent.find("h3")
                        if h3_sibling:
                            title = h3_sibling.get_text(strip=True)

                if not title:
                    link_text = link.get_text(strip=True)
                    if 3 < len(link_text) < 200:
                        title = link_text

                if title:
                    add_result(href, title, "rso_links")

        # 방법 2: h3 셀렉터들
        if len(results) < 5:
            h3_selectors = [
                "h3.LC20lb", "h3.DKV0Md", "h3.MBeuO",
                "h3.zBAuLc", "h3.qsLff",
                "a.zReHs h3", "div.yuRUbf h3", "div.kb0PBd h3",
            ]

            for selector in h3_selectors:
                h3_titles = soup.select(selector)
                for h3 in h3_titles:
                    try:
                        parent_a = h3.find_parent("a")
                        if not parent_a:
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

        # 방법 3: div.g
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

        # 방법 4: data-ved 링크
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

        # 방법 5: cite 근처 링크
        if len(results) < 5:
            cites = soup.find_all("cite")
            for cite in cites:
                try:
                    parent = cite.find_parent(["div", "span"])
                    if parent:
                        link = parent.find_parent("a") or parent.find("a", href=True)
                        if link:
                            href = link.get("href", "")
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

        # 방법 6: 모든 외부 링크
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

        if not debug:
            for r in results:
                r.pop("_method", None)

        return results

    def _find_domain_rank(self, results: List[Dict], target_domain: str) -> Dict:
        """검색 결과에서 타겟 도메인의 순위를 찾습니다."""
        for rank, result in enumerate(results, start=1):
            result_url = result.get("url", "")
            try:
                parsed = urlparse(result_url)
                result_domain = parsed.netloc.lower()

                if result_domain.startswith("www."):
                    result_domain = result_domain[4:]

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

    def __del__(self):
        """소멸자에서 드라이버 정리"""
        self._close_driver()


def main():
    """테스트용 메인 함수"""
    import sys

    debug_mode = "--debug" in sys.argv
    headless = "--no-headless" not in sys.argv

    print(f"Selenium 모드로 실행 (headless={headless})")

    checker = GoogleRankChecker(headless=headless)

    try:
        result = checker.check_rank(
            keyword="노트북 추천",
            target_domain="coupang.com",
            max_results=50,
            debug=debug_mode
        )

        print(f"\n키워드: {result['keyword']}")
        print(f"타겟 도메인: {result['target_domain']}")

        if result['found']:
            print(f"순위: {result['rank']}위")
            print(f"URL: {result['url']}")
            print(f"제목: {result['title']}")
        else:
            print(f"순위: 100위 밖 (확인된 결과: {result['total_checked']}개)")
            if result['error']:
                print(f"오류: {result['error']}")

        if debug_mode and "debug" in result:
            print("\n=== 디버그 정보 ===")
            debug_info = result["debug"]
            print(f"검색 URL: {debug_info.get('search_url', 'N/A')}")
            print(f"페이지 제목: {debug_info.get('page_title', 'N/A')}")
            print(f"응답 길이: {debug_info.get('response_length', 0):,} bytes")
            print(f"#rso 존재: {debug_info.get('has_rso', False)}")
            print(f"h3 개수: {debug_info.get('h3_count', 0)}")
            print(f"div.g 개수: {debug_info.get('div_g_count', 0)}")

            print(f"\n추출된 결과 (상위 10개):")
            for i, r in enumerate(debug_info.get("extracted_results", []), 1):
                print(f"  {i}. {r.get('title', '')[:50]}")
                print(f"     URL: {r.get('url', '')[:70]}")

    finally:
        checker._close_driver()


if __name__ == "__main__":
    main()
