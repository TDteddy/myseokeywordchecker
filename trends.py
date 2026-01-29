"""
네이버 데이터랩 검색어 트렌드 API를 활용한 키워드 인기도 분석 모듈
네이버 통합검색에서의 검색 추이 데이터를 조회합니다.
"""

import os
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv


class TrendsAnalyzer:
    """네이버 데이터랩 검색어 트렌드를 분석하는 클래스"""

    API_URL = "https://openapi.naver.com/v1/datalab/search"

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """
        Args:
            client_id: 네이버 API 클라이언트 ID
            client_secret: 네이버 API 클라이언트 시크릿
        """
        load_dotenv()
        self.client_id = client_id or os.getenv("NAVER_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("NAVER_CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            print("⚠️ 네이버 API 키가 설정되지 않았습니다. NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 환경변수를 설정하세요.")

    def _get_date_range(self, timeframe: str = "today 3-m") -> tuple:
        """
        timeframe 문자열을 시작/종료 날짜로 변환합니다.

        Args:
            timeframe: 'today 1-m', 'today 3-m', 'today 12-m' 등

        Returns:
            (start_date, end_date) 튜플 (yyyy-mm-dd 형식)
        """
        today = datetime.now()
        end_date = today.strftime("%Y-%m-%d")

        # timeframe 파싱
        if "1-m" in timeframe:
            start = today - timedelta(days=30)
        elif "3-m" in timeframe:
            start = today - timedelta(days=90)
        elif "6-m" in timeframe:
            start = today - timedelta(days=180)
        elif "12-m" in timeframe:
            start = today - timedelta(days=365)
        else:
            # 기본값: 3개월
            start = today - timedelta(days=90)

        start_date = start.strftime("%Y-%m-%d")
        return start_date, end_date

    def get_keyword_interest(
        self,
        keywords: List[str],
        timeframe: str = "today 3-m",
        geo: str = "KR",
    ) -> Dict:
        """
        키워드들의 상대적 인기도를 조회합니다.

        Args:
            keywords: 비교할 키워드 목록 (최대 5개)
            timeframe: 조회 기간 (기본: 최근 3개월)
            geo: 지역 코드 (네이버는 한국만 지원)

        Returns:
            키워드별 인기도 점수 및 트렌드 정보
        """
        if not self.client_id or not self.client_secret:
            return {"error": "네이버 API 키가 설정되지 않았습니다.", "keywords": []}

        # 최대 5개 키워드만 비교 가능
        keywords = keywords[:5]

        if not keywords:
            return {"error": "키워드가 필요합니다", "keywords": []}

        try:
            start_date, end_date = self._get_date_range(timeframe)

            # 키워드 그룹 구성 (각 키워드를 개별 그룹으로)
            keyword_groups = []
            for kw in keywords:
                keyword_groups.append({
                    "groupName": kw,
                    "keywords": [kw]
                })

            # API 요청 데이터
            request_body = {
                "startDate": start_date,
                "endDate": end_date,
                "timeUnit": "week",  # 주간 단위
                "keywordGroups": keyword_groups
            }

            # API 호출
            headers = {
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
                "Content-Type": "application/json"
            }

            response = requests.post(
                self.API_URL,
                headers=headers,
                json=request_body,
                timeout=30
            )

            if response.status_code != 200:
                error_msg = f"네이버 API 오류: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('errorMessage', '')}"
                except:
                    pass
                return {"error": error_msg, "keywords": []}

            data = response.json()

            # 결과 처리
            result = {
                "keywords": [],
                "comparison": {},
                "timeframe": timeframe,
                "source": "naver_datalab"
            }

            results = data.get("results", [])
            if not results:
                for kw in keywords:
                    result["keywords"].append({
                        "keyword": kw,
                        "score": 0,
                        "avg_interest": 0,
                        "max_interest": 0,
                        "trend": "데이터 없음",
                    })
                return result

            # 각 키워드별 점수 계산
            for kw_result in results:
                kw_name = kw_result.get("title", "")
                kw_data = kw_result.get("data", [])

                if not kw_data:
                    result["keywords"].append({
                        "keyword": kw_name,
                        "score": 0,
                        "avg_interest": 0,
                        "max_interest": 0,
                        "trend": "데이터 없음",
                    })
                    continue

                # ratio 값 추출
                ratios = [d.get("ratio", 0) for d in kw_data]

                if not ratios:
                    result["keywords"].append({
                        "keyword": kw_name,
                        "score": 0,
                        "avg_interest": 0,
                        "max_interest": 0,
                        "trend": "데이터 없음",
                    })
                    continue

                avg_interest = sum(ratios) / len(ratios)
                max_interest = max(ratios)
                current_interest = ratios[-1] if ratios else 0

                # 트렌드 방향 계산 (최근 vs 이전)
                if len(ratios) >= 4:
                    recent_avg = sum(ratios[-3:]) / 3  # 최근 3주
                    older_avg = sum(ratios[:-3]) / len(ratios[:-3]) if len(ratios) > 3 else recent_avg

                    if older_avg > 0:
                        change_pct = ((recent_avg - older_avg) / older_avg) * 100
                        if change_pct > 15:
                            trend = "상승"
                        elif change_pct < -15:
                            trend = "하락"
                        else:
                            trend = "유지"
                    else:
                        trend = "신규" if recent_avg > 0 else "데이터 없음"
                else:
                    trend = "데이터 부족"

                result["keywords"].append({
                    "keyword": kw_name,
                    "score": round(current_interest, 1),
                    "avg_interest": round(avg_interest, 1),
                    "max_interest": round(max_interest, 1),
                    "trend": trend,
                })

            # 점수 기준 정렬
            result["keywords"].sort(key=lambda x: x["score"], reverse=True)

            # 1위 키워드 대비 비율 계산
            if result["keywords"] and result["keywords"][0]["score"] > 0:
                top_score = result["keywords"][0]["score"]
                for kw_data in result["keywords"]:
                    kw_data["relative_score"] = round(
                        (kw_data["score"] / top_score) * 100, 1
                    )
            else:
                for kw_data in result["keywords"]:
                    kw_data["relative_score"] = 0

            return result

        except requests.exceptions.Timeout:
            return {"error": "네이버 API 타임아웃", "keywords": []}
        except requests.exceptions.RequestException as e:
            return {"error": f"네이버 API 연결 오류: {str(e)}", "keywords": []}
        except Exception as e:
            return {"error": f"트렌드 조회 오류: {str(e)}", "keywords": []}

    def get_related_queries(
        self,
        keyword: str,
        geo: str = "KR",
        timeframe: str = "today 3-m",
    ) -> Dict:
        """
        키워드와 관련된 검색어를 조회합니다.

        참고: 네이버 데이터랩 API는 관련 검색어 기능을 제공하지 않습니다.
        대신 빈 결과를 반환하고, 키워드 확장 기능을 사용하는 것을 권장합니다.

        Args:
            keyword: 조회할 키워드
            geo: 지역 코드
            timeframe: 조회 기간

        Returns:
            관련 검색어 목록 (네이버 API는 미지원)
        """
        # 네이버 데이터랩은 관련 검색어 API를 제공하지 않음
        # GPT 키워드 확장 기능으로 대체
        return {
            "keyword": keyword,
            "top_queries": [],
            "rising_queries": [],
            "note": "네이버 데이터랩은 관련 검색어를 제공하지 않습니다. 키워드 확장 기능을 활용하세요."
        }

    def compare_keywords_batch(
        self,
        all_keywords: List[str],
        geo: str = "KR",
        timeframe: str = "today 3-m",
    ) -> List[Dict]:
        """
        5개 이상의 키워드를 배치로 비교합니다.
        네이버 API는 한 번에 5개까지만 비교 가능하므로,
        기준 키워드를 두고 상대적 비교를 수행합니다.

        Args:
            all_keywords: 비교할 전체 키워드 목록
            geo: 지역 코드
            timeframe: 조회 기간

        Returns:
            모든 키워드의 정규화된 점수 목록
        """
        if not all_keywords:
            return []

        # 5개 이하면 바로 조회
        if len(all_keywords) <= 5:
            result = self.get_keyword_interest(all_keywords, timeframe, geo)
            return result.get("keywords", [])

        # 첫 번째 키워드를 기준으로 사용
        reference_kw = all_keywords[0]
        all_results = {}

        # 첫 번째 배치 (기준 키워드 포함)
        first_batch = all_keywords[:5]
        first_result = self.get_keyword_interest(first_batch, timeframe, geo)

        if "error" in first_result:
            return []

        reference_score = 0
        for kw_data in first_result.get("keywords", []):
            all_results[kw_data["keyword"]] = kw_data
            if kw_data["keyword"] == reference_kw:
                reference_score = kw_data["score"]

        # 나머지 배치 처리 (기준 키워드 포함하여 비교)
        remaining = all_keywords[5:]
        for i in range(0, len(remaining), 4):
            batch = [reference_kw] + remaining[i : i + 4]
            time.sleep(0.5)  # Rate limiting (네이버 API 제한 고려)

            batch_result = self.get_keyword_interest(batch, timeframe, geo)

            if "error" not in batch_result:
                # 기준 키워드의 이 배치에서의 점수
                batch_ref_score = 0
                for kw_data in batch_result.get("keywords", []):
                    if kw_data["keyword"] == reference_kw:
                        batch_ref_score = kw_data["score"]
                        break

                # 점수 정규화
                if batch_ref_score > 0 and reference_score > 0:
                    scale_factor = reference_score / batch_ref_score
                else:
                    scale_factor = 1

                for kw_data in batch_result.get("keywords", []):
                    if kw_data["keyword"] != reference_kw:
                        normalized_score = kw_data["score"] * scale_factor
                        kw_data["score"] = min(round(normalized_score, 1), 100)
                        all_results[kw_data["keyword"]] = kw_data

        # 결과를 리스트로 변환하고 점수순 정렬
        final_results = list(all_results.values())
        final_results.sort(key=lambda x: x["score"], reverse=True)

        # 상대 점수 재계산
        if final_results and final_results[0]["score"] > 0:
            top_score = final_results[0]["score"]
            for kw_data in final_results:
                kw_data["relative_score"] = round((kw_data["score"] / top_score) * 100, 1)

        return final_results


def main():
    """테스트용 메인 함수"""
    analyzer = TrendsAnalyzer()

    # 테스트 키워드
    keywords = ["무드등", "LED 조명", "인테리어 조명", "취침등", "수면등"]

    print("네이버 데이터랩 키워드 인기도 비교:")
    result = analyzer.get_keyword_interest(keywords)

    if "error" in result:
        print(f"오류: {result['error']}")
    else:
        for kw in result["keywords"]:
            print(
                f"  {kw['keyword']}: {kw['score']}점 "
                f"(평균: {kw['avg_interest']}, 트렌드: {kw['trend']})"
            )


if __name__ == "__main__":
    main()
