"""
회사 내부 키워드 성과 데이터 API 모듈
실제 구매/유입 키워드 데이터를 조회합니다.
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class CompanyKeywordAPI:
    """회사 키워드 성과 데이터를 조회하는 클래스"""

    API_URL = "https://bryze.kr:8000/get_keyword_data"

    # Type 코드 정의
    TYPE_NAVER_ORGANIC = 4  # 네이버 오가닉

    def __init__(self):
        """초기화"""
        pass

    def get_keyword_data(
        self,
        brand: Optional[str] = None,
        product_line: Optional[str] = None,
        product_group: Optional[str] = None,
        product_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        naver_organic_only: bool = True
    ) -> Dict:
        """
        키워드 성과 데이터를 조회합니다.

        Args:
            brand: 브랜드명
            product_line: 제품 라인
            product_group: 제품 그룹
            product_name: 제품명
            start_date: 시작일 (yyyy-mm-dd)
            end_date: 종료일 (yyyy-mm-dd)
            naver_organic_only: True면 네이버 오가닉(Type 4)만 필터링

        Returns:
            키워드별 클릭/구매 데이터
        """
        # 기본 날짜 설정 (최근 30일)
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start = datetime.now() - timedelta(days=30)
            start_date = start.strftime("%Y-%m-%d")

        # 요청 파라미터 구성
        params = {
            "start_date": start_date,
            "end_date": end_date
        }

        if brand:
            params["brand"] = brand
        if product_line:
            params["product_line"] = product_line
        if product_group:
            params["product_group"] = product_group
        if product_name:
            params["product_name"] = product_name

        try:
            response = requests.get(
                self.API_URL,
                params=params,
                timeout=30,
                verify=True  # SSL 인증서 검증
            )

            if response.status_code != 200:
                return {
                    "error": f"API 오류: {response.status_code}",
                    "keywords": []
                }

            data = response.json()

            # 데이터가 리스트인 경우 처리
            if isinstance(data, list):
                raw_data = data
            elif isinstance(data, dict) and "data" in data:
                raw_data = data["data"]
            else:
                raw_data = []

            # 네이버 오가닉(Type 4)만 필터링
            if naver_organic_only:
                raw_data = [
                    item for item in raw_data
                    if item.get("Type") == self.TYPE_NAVER_ORGANIC
                ]

            # 키워드별 집계
            keyword_stats = self._aggregate_keywords(raw_data)

            return {
                "keywords": keyword_stats,
                "period": {
                    "start": start_date,
                    "end": end_date
                },
                "total_keywords": len(keyword_stats),
                "source": "company_api"
            }

        except requests.exceptions.Timeout:
            return {"error": "API 타임아웃", "keywords": []}
        except requests.exceptions.SSLError as e:
            return {"error": f"SSL 오류: {str(e)}", "keywords": []}
        except requests.exceptions.RequestException as e:
            return {"error": f"API 연결 오류: {str(e)}", "keywords": []}
        except Exception as e:
            return {"error": f"데이터 조회 오류: {str(e)}", "keywords": []}

    def _aggregate_keywords(self, raw_data: List[Dict]) -> List[Dict]:
        """
        키워드별로 클릭수, 구매수를 집계합니다.

        Args:
            raw_data: API 원본 데이터

        Returns:
            키워드별 집계 데이터
        """
        keyword_map = {}

        for item in raw_data:
            keyword = item.get("Keyword", "").strip()
            if not keyword:
                continue

            clicks = item.get("Count_click", 0) or 0
            orders = item.get("Count_order", 0) or 0

            if keyword not in keyword_map:
                keyword_map[keyword] = {
                    "keyword": keyword,
                    "clicks": 0,
                    "orders": 0,
                    "dates": set()
                }

            keyword_map[keyword]["clicks"] += clicks
            keyword_map[keyword]["orders"] += orders

            date = item.get("Date", "")
            if date:
                keyword_map[keyword]["dates"].add(date)

        # 결과 정리
        results = []
        for keyword, stats in keyword_map.items():
            # 전환율 계산
            conversion_rate = 0
            if stats["clicks"] > 0:
                conversion_rate = (stats["orders"] / stats["clicks"]) * 100

            results.append({
                "keyword": keyword,
                "clicks": stats["clicks"],
                "orders": stats["orders"],
                "conversion_rate": round(conversion_rate, 2),
                "days_active": len(stats["dates"])
            })

        # 구매수 > 클릭수 순으로 정렬
        results.sort(key=lambda x: (x["orders"], x["clicks"]), reverse=True)

        return results

    def get_top_converting_keywords(
        self,
        limit: int = 20,
        min_clicks: int = 5,
        **kwargs
    ) -> List[Dict]:
        """
        전환율이 높은 상위 키워드를 조회합니다.

        Args:
            limit: 반환할 키워드 수
            min_clicks: 최소 클릭수 (노이즈 제거)
            **kwargs: get_keyword_data에 전달할 파라미터

        Returns:
            전환율 상위 키워드 목록
        """
        result = self.get_keyword_data(**kwargs)

        if "error" in result:
            return []

        keywords = result.get("keywords", [])

        # 최소 클릭수 필터링
        filtered = [kw for kw in keywords if kw["clicks"] >= min_clicks]

        # 전환율 순 정렬
        filtered.sort(key=lambda x: x["conversion_rate"], reverse=True)

        return filtered[:limit]

    def get_top_volume_keywords(
        self,
        limit: int = 20,
        **kwargs
    ) -> List[Dict]:
        """
        클릭/구매 볼륨이 높은 상위 키워드를 조회합니다.

        Args:
            limit: 반환할 키워드 수
            **kwargs: get_keyword_data에 전달할 파라미터

        Returns:
            볼륨 상위 키워드 목록
        """
        result = self.get_keyword_data(**kwargs)

        if "error" in result:
            return []

        keywords = result.get("keywords", [])

        # 이미 구매수 > 클릭수 순으로 정렬됨
        return keywords[:limit]

    def analyze_keyword_performance(
        self,
        target_keywords: List[str],
        **kwargs
    ) -> Dict:
        """
        특정 키워드들의 실제 성과를 분석합니다.

        Args:
            target_keywords: 분석할 키워드 목록
            **kwargs: get_keyword_data에 전달할 파라미터

        Returns:
            키워드별 성과 분석 결과
        """
        result = self.get_keyword_data(**kwargs)

        if "error" in result:
            return {"error": result["error"], "found": [], "not_found": []}

        all_keywords = {kw["keyword"].lower(): kw for kw in result.get("keywords", [])}

        found = []
        not_found = []

        for target in target_keywords:
            target_lower = target.lower()

            # 정확히 일치하는 키워드 찾기
            if target_lower in all_keywords:
                found.append(all_keywords[target_lower])
            else:
                # 부분 일치 검색
                partial_matches = [
                    kw_data for kw, kw_data in all_keywords.items()
                    if target_lower in kw or kw in target_lower
                ]
                if partial_matches:
                    # 가장 성과 좋은 것 선택
                    best_match = max(partial_matches, key=lambda x: x["orders"])
                    found.append({
                        **best_match,
                        "matched_from": target
                    })
                else:
                    not_found.append(target)

        return {
            "found": found,
            "not_found": not_found,
            "match_rate": len(found) / len(target_keywords) * 100 if target_keywords else 0
        }


def main():
    """테스트용 메인 함수"""
    api = CompanyKeywordAPI()

    print("회사 키워드 성과 데이터 조회 테스트:")
    result = api.get_keyword_data()

    if "error" in result:
        print(f"오류: {result['error']}")
    else:
        print(f"조회된 키워드 수: {result['total_keywords']}")
        print(f"조회 기간: {result['period']['start']} ~ {result['period']['end']}")

        print("\n상위 10개 키워드 (구매순):")
        for kw in result["keywords"][:10]:
            print(f"  {kw['keyword']}: 클릭 {kw['clicks']}, 구매 {kw['orders']}, 전환율 {kw['conversion_rate']}%")


if __name__ == "__main__":
    main()
