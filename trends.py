"""
Google Trends API를 활용한 키워드 인기도 분석 모듈
pytrends 라이브러리를 사용하여 키워드 간 상대적 인기도를 비교합니다.
"""

import time
from typing import List, Dict, Optional
from pytrends.request import TrendReq


class TrendsAnalyzer:
    """Google Trends 데이터를 분석하는 클래스"""

    def __init__(self, hl: str = "ko", tz: int = 540):
        """
        Args:
            hl: 언어 설정 (기본: 한국어)
            tz: 타임존 오프셋 (기본: 540 = 한국 KST)
        """
        self.hl = hl
        self.tz = tz
        self.pytrends = None
        self._init_pytrends()

    def _init_pytrends(self):
        """pytrends 인스턴스 초기화"""
        try:
            self.pytrends = TrendReq(hl=self.hl, tz=self.tz, timeout=(10, 25))
        except Exception as e:
            print(f"pytrends 초기화 오류: {e}")
            self.pytrends = None

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
                - 'today 1-m': 최근 1개월
                - 'today 3-m': 최근 3개월
                - 'today 12-m': 최근 12개월
            geo: 지역 코드 (기본: KR = 한국)

        Returns:
            키워드별 인기도 점수 및 트렌드 정보
        """
        if not self.pytrends:
            return {"error": "Google Trends 연결 실패", "keywords": []}

        # 최대 5개 키워드만 비교 가능
        keywords = keywords[:5]

        if not keywords:
            return {"error": "키워드가 필요합니다", "keywords": []}

        try:
            # 키워드 빌드
            self.pytrends.build_payload(
                kw_list=keywords,
                cat=0,
                timeframe=timeframe,
                geo=geo,
                gprop="",
            )

            # 시간별 관심도 데이터
            interest_over_time = self.pytrends.interest_over_time()

            # 결과 처리
            result = {
                "keywords": [],
                "comparison": {},
                "timeframe": timeframe,
                "geo": geo,
            }

            if interest_over_time.empty:
                # 데이터가 없는 경우 모든 키워드에 0점 부여
                for kw in keywords:
                    result["keywords"].append(
                        {
                            "keyword": kw,
                            "score": 0,
                            "avg_interest": 0,
                            "max_interest": 0,
                            "trend": "데이터 없음",
                        }
                    )
                return result

            # 각 키워드별 점수 계산
            for kw in keywords:
                if kw in interest_over_time.columns:
                    data = interest_over_time[kw]
                    avg_interest = float(data.mean())
                    max_interest = int(data.max())
                    current_interest = int(data.iloc[-1]) if len(data) > 0 else 0

                    # 트렌드 방향 계산 (최근 vs 이전)
                    if len(data) > 4:
                        recent_avg = data.iloc[-4:].mean()
                        older_avg = data.iloc[:-4].mean()
                        if older_avg > 0:
                            change_pct = ((recent_avg - older_avg) / older_avg) * 100
                            if change_pct > 10:
                                trend = "상승"
                            elif change_pct < -10:
                                trend = "하락"
                            else:
                                trend = "유지"
                        else:
                            trend = "신규"
                    else:
                        trend = "데이터 부족"

                    result["keywords"].append(
                        {
                            "keyword": kw,
                            "score": current_interest,
                            "avg_interest": round(avg_interest, 1),
                            "max_interest": max_interest,
                            "trend": trend,
                        }
                    )
                else:
                    result["keywords"].append(
                        {
                            "keyword": kw,
                            "score": 0,
                            "avg_interest": 0,
                            "max_interest": 0,
                            "trend": "데이터 없음",
                        }
                    )

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

        except Exception as e:
            return {"error": f"Google Trends 조회 오류: {str(e)}", "keywords": []}

    def get_related_queries(
        self,
        keyword: str,
        geo: str = "KR",
        timeframe: str = "today 3-m",
    ) -> Dict:
        """
        키워드와 관련된 검색어를 조회합니다.

        Args:
            keyword: 조회할 키워드
            geo: 지역 코드
            timeframe: 조회 기간

        Returns:
            관련 검색어 목록 (인기/급상승)
        """
        if not self.pytrends:
            return {"error": "Google Trends 연결 실패"}

        try:
            self.pytrends.build_payload(
                kw_list=[keyword],
                cat=0,
                timeframe=timeframe,
                geo=geo,
                gprop="",
            )

            related = self.pytrends.related_queries()

            result = {
                "keyword": keyword,
                "top_queries": [],
                "rising_queries": [],
            }

            if keyword in related:
                kw_data = related[keyword]

                # 인기 검색어
                if kw_data.get("top") is not None and not kw_data["top"].empty:
                    for _, row in kw_data["top"].head(10).iterrows():
                        result["top_queries"].append(
                            {
                                "query": row["query"],
                                "value": int(row["value"]),
                            }
                        )

                # 급상승 검색어
                if kw_data.get("rising") is not None and not kw_data["rising"].empty:
                    for _, row in kw_data["rising"].head(10).iterrows():
                        result["rising_queries"].append(
                            {
                                "query": row["query"],
                                "value": str(row["value"]),
                            }
                        )

            return result

        except Exception as e:
            return {"error": f"관련 검색어 조회 오류: {str(e)}"}

    def compare_keywords_batch(
        self,
        all_keywords: List[str],
        geo: str = "KR",
        timeframe: str = "today 3-m",
    ) -> List[Dict]:
        """
        5개 이상의 키워드를 배치로 비교합니다.
        Google Trends는 한 번에 5개까지만 비교 가능하므로,
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
            time.sleep(1)  # Rate limiting

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
                        normalized_score = int(kw_data["score"] * scale_factor)
                        kw_data["score"] = min(normalized_score, 100)
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

    print("키워드 인기도 비교:")
    result = analyzer.get_keyword_interest(keywords)

    if "error" in result:
        print(f"오류: {result['error']}")
    else:
        for kw in result["keywords"]:
            print(
                f"  {kw['keyword']}: {kw['score']}점 "
                f"(평균: {kw['avg_interest']}, 트렌드: {kw['trend']})"
            )

    print("\n관련 검색어:")
    related = analyzer.get_related_queries("무드등")
    if "error" not in related:
        print("  인기 검색어:", [q["query"] for q in related["top_queries"][:5]])
        print("  급상승 검색어:", [q["query"] for q in related["rising_queries"][:5]])


if __name__ == "__main__":
    main()
