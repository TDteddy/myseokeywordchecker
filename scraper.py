"""
웹페이지 스크래핑 모듈
URL에서 SEO 관련 요소들을 추출합니다.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Optional


class WebScraper:
    """웹페이지에서 SEO 관련 정보를 추출하는 클래스"""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def fetch_page(self, url: str) -> Optional[str]:
        """URL에서 HTML 콘텐츠를 가져옵니다."""
        try:
            response = requests.get(
                url, headers=self.headers, timeout=self.timeout, allow_redirects=True
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text
        except requests.RequestException as e:
            print(f"페이지 가져오기 실패: {e}")
            return None

    def extract_seo_elements(self, url: str) -> Optional[dict]:
        """URL에서 SEO 관련 요소들을 추출합니다."""
        html = self.fetch_page(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")

        # 기본 정보
        parsed_url = urlparse(url)

        seo_data = {
            "url": url,
            "domain": parsed_url.netloc,
            "path": parsed_url.path,
            "title": self._extract_title(soup),
            "meta_description": self._extract_meta_description(soup),
            "meta_keywords": self._extract_meta_keywords(soup),
            "og_tags": self._extract_og_tags(soup),
            "headings": self._extract_headings(soup),
            "links": self._extract_links(soup, parsed_url.netloc),
            "images": self._extract_images(soup),
            "body_text": self._extract_body_text(soup),
            "canonical": self._extract_canonical(soup),
            "robots": self._extract_robots(soup),
            "schema_markup": self._extract_schema_markup(soup),
        }

        return seo_data

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """페이지 제목 추출"""
        title_tag = soup.find("title")
        return title_tag.get_text(strip=True) if title_tag else ""

    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """메타 설명 추출"""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            return meta.get("content", "")
        return ""

    def _extract_meta_keywords(self, soup: BeautifulSoup) -> str:
        """메타 키워드 추출"""
        meta = soup.find("meta", attrs={"name": "keywords"})
        if meta:
            return meta.get("content", "")
        return ""

    def _extract_og_tags(self, soup: BeautifulSoup) -> dict:
        """Open Graph 태그 추출"""
        og_tags = {}
        for meta in soup.find_all("meta", attrs={"property": True}):
            prop = meta.get("property", "")
            if prop.startswith("og:"):
                og_tags[prop] = meta.get("content", "")
        return og_tags

    def _extract_headings(self, soup: BeautifulSoup) -> dict:
        """H1-H6 헤딩 태그 추출"""
        headings = {}
        for i in range(1, 7):
            tag = f"h{i}"
            elements = soup.find_all(tag)
            headings[tag] = [el.get_text(strip=True) for el in elements]
        return headings

    def _extract_links(self, soup: BeautifulSoup, domain: str) -> dict:
        """내부/외부 링크 추출"""
        internal_links = []
        external_links = []

        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            text = a.get_text(strip=True)

            if href.startswith("#") or href.startswith("javascript:"):
                continue

            link_info = {"href": href, "text": text[:100]}

            if href.startswith("/") or domain in href:
                internal_links.append(link_info)
            elif href.startswith("http"):
                external_links.append(link_info)

        return {
            "internal": internal_links[:50],  # 최대 50개
            "external": external_links[:30],  # 최대 30개
            "internal_count": len(internal_links),
            "external_count": len(external_links),
        }

    def _extract_images(self, soup: BeautifulSoup) -> list:
        """이미지 alt 텍스트 추출"""
        images = []
        for img in soup.find_all("img"):
            alt = img.get("alt", "")
            src = img.get("src", "")
            if alt or src:
                images.append({"src": src[:200], "alt": alt})
        return images[:30]  # 최대 30개

    def _extract_body_text(self, soup: BeautifulSoup) -> str:
        """본문 텍스트 추출 (스크립트, 스타일 제외)"""
        # 불필요한 태그 제거
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()

        # 본문 텍스트 추출
        body = soup.find("body")
        if body:
            text = body.get_text(separator=" ", strip=True)
            # 연속된 공백 제거
            text = " ".join(text.split())
            return text[:5000]  # 최대 5000자
        return ""

    def _extract_canonical(self, soup: BeautifulSoup) -> str:
        """Canonical URL 추출"""
        link = soup.find("link", attrs={"rel": "canonical"})
        if link:
            return link.get("href", "")
        return ""

    def _extract_robots(self, soup: BeautifulSoup) -> str:
        """Robots 메타 태그 추출"""
        meta = soup.find("meta", attrs={"name": "robots"})
        if meta:
            return meta.get("content", "")
        return ""

    def _extract_schema_markup(self, soup: BeautifulSoup) -> list:
        """JSON-LD Schema 마크업 추출"""
        schemas = []
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                content = script.string
                if content:
                    schemas.append(content[:1000])  # 최대 1000자씩
            except Exception:
                pass
        return schemas[:5]  # 최대 5개


def main():
    """테스트용 메인 함수"""
    scraper = WebScraper()
    url = input("분석할 URL을 입력하세요: ")
    data = scraper.extract_seo_elements(url)

    if data:
        print("\n=== SEO 요소 추출 결과 ===")
        print(f"제목: {data['title']}")
        print(f"메타 설명: {data['meta_description']}")
        print(f"메타 키워드: {data['meta_keywords']}")
        print(f"H1 태그: {data['headings'].get('h1', [])}")
        print(f"내부 링크 수: {data['links']['internal_count']}")
        print(f"외부 링크 수: {data['links']['external_count']}")


if __name__ == "__main__":
    main()
