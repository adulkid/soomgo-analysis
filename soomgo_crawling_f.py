"""
숨고 크롤러 (카테고리별 수집)
==================
Phase A: 카테고리별 고수 목록 수집 (sort=hired_count, 269개 카테고리 × 100명)
Phase B: 상세 데이터 수집 (리뷰, 리뷰태그, 포트폴리오)

실행:
  python soomgo_crawling_f.py --phase a        # 고수 목록 수집
  python soomgo_crawling_f.py --phase b        # 상세 데이터 수집
  python soomgo_crawling_f.py --phase a --test # 3개 카테고리만 테스트
"""

import requests
import pandas as pd
import csv
import time
import os
import argparse
from datetime import datetime


# ============================================================
# 설정
# ============================================================
BASE_URL = "https://api.soomgo.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Accept": "application/json",
    "Referer": "https://soomgo.com/",
    "Origin": "https://soomgo.com",
}
DELAY_SEARCH = 0.3   # 목록 API 딜레이
DELAY_DETAIL = 0.7   # 상세 API 딜레이

# 입력 (원본 - 절대 수정 금지)
SOURCE_FILE = "soomgo_pros.csv"

# 출력 (새로 수집)
PROS_FILE        = "soomgo_pros_f.csv"
REVIEWS_FILE     = "soomgo_reviews_f.csv"
REVIEW_TAGS_FILE = "soomgo_review_tags_f.csv"
PORTFOLIOS_FILE  = "soomgo_portfolios_f.csv"
LOG_FILE         = "crawl_log.txt"

# 카테고리당 수집 목표
TARGET_PER_CATEGORY = 100


# ============================================================
# 유틸리티 함수
# ============================================================
def log(msg):
    """타임스탬프 포함 콘솔 출력 + 파일 기록"""
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def fetch_api(endpoint, params=None, retries=3):
    """API 호출 - 재시도 로직 포함"""
    url = f"{BASE_URL}{endpoint}"
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                wait = 10 * (attempt + 1)
                log(f"  ⚠ Rate limit! {wait}초 대기...")
                time.sleep(wait)
                continue
            else:
                return None
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(5)
            else:
                log(f"  ❌ 요청 실패: {e}")
                return None
    return None


def append_rows_to_csv(filepath, rows, fieldnames):
    """CSV에 행 추가 저장 (append 모드)"""
    file_exists = os.path.exists(filepath)
    with open(filepath, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


# ============================================================
# 카테고리 추출
# ============================================================
def extract_categories(source_file):
    """
    기존 CSV에서 두 가지 기준으로 카테고리 추출 후 합집합 반환
    - 고용횟수 합산 상위 200개
    - 고수 수 상위 200개
    """
    df = pd.read_csv(source_file, encoding="utf-8")
    df = df.dropna(subset=["main_service"])

    # 기준 1: 고용횟수 합산 상위 200
    top200_hired = set(
        df.groupby("main_service")["hired_count"]
        .sum()
        .sort_values(ascending=False)
        .head(200)
        .index.tolist()
    )

    # 기준 2: 고수 수 상위 200
    top200_gosu = set(
        df.groupby("main_service")["id"]
        .count()
        .sort_values(ascending=False)
        .head(200)
        .index.tolist()
    )

    # 합집합
    keywords = list(top200_hired | top200_gosu)
    log(f"  카테고리 추출 완료: 고용횟수 기준 {len(top200_hired)}개 + 고수수 기준 {len(top200_gosu)}개 → 합집합 {len(keywords)}개")
    return keywords


# ============================================================
# Phase A: 카테고리별 고수 목록 수집
# ============================================================
def phase_a(test_mode=False):
    log("=" * 60)
    log("Phase A: 카테고리별 고수 목록 수집")
    log("=" * 60)

    # 카테고리 추출
    keywords = extract_categories(SOURCE_FILE)

    if test_mode:
        keywords = keywords[:3]
        log(f"  테스트 모드: {len(keywords)}개 카테고리만 수집")

    # 재시작 대비: 이미 수집된 user_id 로드
    seen_user_ids = (
        set(pd.read_csv(PROS_FILE, encoding="utf-8-sig")["user_id"].astype(str))
        if os.path.exists(PROS_FILE)
        else set()
    )
    log(f"  이미 수집된 고수: {len(seen_user_ids)}명")

    pros_fields = [
        "provider_id", "user_id", "name", "address", "career",
        "review_count", "hired_count", "review_rate", "safe_payment_count",
        "avg_response_time", "main_service", "service_count",
        "is_safe_payment", "can_reserve", "is_ambassador",
        "recent_review_rate", "recent_review_text",
    ]

    total_collected = len(seen_user_ids)

    for cat_idx, category in enumerate(keywords):
        count = 0
        cursor = None
        batch = []

        while True:
            params = {
                "sort": "hired_count",
                "keyword": category,
                "can_reserve": "false",
                "is_promotion_target": "false",
            }
            if cursor:
                params["cursor"] = cursor

            data = fetch_api("/v2/search/pro", params=params)
            if not data:
                log(f"  [{cat_idx+1}/{len(keywords)}] {category} - API 호출 실패, 스킵")
                break

            results = data.get("response", {}).get("results", [])
            cursor = data.get("response", {}).get("cursor")

            if not results:
                break

            for pro in results:
                score        = pro.get("score") or {}
                main_service = pro.get("mainService") or {}
                recent_review= pro.get("recentReview") or {}
                services     = pro.get("services") or []
                user         = pro.get("user") or {}

                user_id = str(user.get("id", ""))
                if not user_id or user_id in seen_user_ids:
                    continue  # 중복 스킵

                seen_user_ids.add(user_id)
                batch.append({
                    "provider_id":        pro.get("id"),
                    "user_id":            user_id,
                    "name":               pro.get("companyName"),
                    "address":            pro.get("address"),
                    "career":             pro.get("career"),
                    "review_count":       score.get("review_count"),
                    "hired_count":        score.get("hired_count"),
                    "review_rate":        score.get("review_rate"),
                    "safe_payment_count": score.get("safe_payment_count"),
                    "avg_response_time":  pro.get("avgResponseTime"),
                    "main_service":       main_service.get("name"),
                    "service_count":      len(services),
                    "is_safe_payment":    pro.get("isSafePayment"),
                    "can_reserve":        pro.get("canReserve"),
                    "is_ambassador":      pro.get("isAmbassador"),
                    "recent_review_rate": recent_review.get("rate"),
                    "recent_review_text": (recent_review.get("contents") or "").replace("\n", " "),
                })
                count += 1

                if count >= TARGET_PER_CATEGORY:
                    break

            # 배치 저장 (페이지마다)
            if batch:
                append_rows_to_csv(PROS_FILE, batch, pros_fields)
                total_collected += len(batch)
                batch = []

            if count >= TARGET_PER_CATEGORY or not cursor:
                break

            time.sleep(DELAY_SEARCH)

        log(f"  [{cat_idx+1}/{len(keywords)}] {category} → {count}명 수집 (누적 {total_collected}명)")

    log(f"\n  Phase A 완료! 총 {total_collected}명 수집")


# ============================================================
# Phase B: 상세 데이터 수집 (리뷰, 태그, 포트폴리오)
# ============================================================
def phase_b(test_mode=False):
    log("=" * 60)
    log("Phase B: 상세 데이터 수집")
    log("=" * 60)

    if not os.path.exists(PROS_FILE):
        log(f"  ❌ {PROS_FILE} 없음. Phase A를 먼저 실행하세요.")
        return

    df = pd.read_csv(PROS_FILE, encoding="utf-8-sig")
    df = df[df["user_id"].notna()].copy()
    df["user_id"]    = df["user_id"].astype(int).astype(str)
    df["provider_id"]= df["provider_id"].astype(int).astype(str)
    log(f"  고수 목록: {len(df)}명")

    # 체크포인트: 이미 수집된 user_id
    done = set()
    if os.path.exists(REVIEW_TAGS_FILE):
        done = set(
            pd.read_csv(REVIEW_TAGS_FILE, encoding="utf-8-sig")["user_id"].astype(str)
        )
    todo_df = df[~df["user_id"].isin(done)]

    if test_mode:
        todo_df = todo_df.head(10)
        log("  테스트 모드: 10명만 수집")

    log(f"  이미 완료: {len(done)}명 / 수집 대상: {len(todo_df)}명")
    est = len(todo_df) * DELAY_DETAIL * 4 / 60
    log(f"  예상 소요: ~{est:.0f}분 ({est/60:.1f}시간)")

    review_tag_fields = [
        "user_id", "provider_id", "avg_rating", "total_review_count",
        "tag_1_text", "tag_1_count", "tag_2_text", "tag_2_count",
        "tag_3_text", "tag_3_count", "tag_4_text", "tag_4_count",
        "tag_5_text", "tag_5_count",
    ]
    review_fields = [
        "user_id", "provider_id", "review_id", "rating", "content",
        "created_at", "survey_tags", "has_image", "image_count", "reviewer_id",
    ]
    portfolio_fields = [
        "user_id", "provider_id", "portfolio_id", "title",
        "service_name", "service_amount", "view_count", "like_count",
        "address1", "address2", "created_at",
    ]

    total = len(todo_df)
    for i, (_, row) in enumerate(todo_df.iterrows()):
        uid = row["user_id"]
        pid = row["provider_id"]

        # 1. 리뷰 태그 요약
        tag_row = {"user_id": uid, "provider_id": pid}
        data = fetch_api(f"/v3/users/{uid}/reviews/received/summary")
        if data and data.get("code") == 0:
            resp = data["response"]
            ri = resp.get("ratingInfo", {})
            tag_row["avg_rating"]         = ri.get("average", "")
            tag_row["total_review_count"] = ri.get("count", 0)
            details = resp.get("surveyInfo", {}).get("details", [])
            for j, s in enumerate(details[:5]):
                tag_row[f"tag_{j+1}_text"]  = s.get("text", "")
                tag_row[f"tag_{j+1}_count"] = s.get("count", 0)
        append_rows_to_csv(REVIEW_TAGS_FILE, [tag_row], review_tag_fields)
        time.sleep(DELAY_DETAIL)

        # 2. 리뷰 목록 (최대 30개)
        reviews = []
        cursor = ""
        for _ in range(3):
            params = {"size": 10}
            if cursor:
                params["cursor"] = cursor
            data = fetch_api(f"/v3/users/{uid}/reviews/received", params=params)
            if not data or data.get("code") != 0:
                break
            resp = data["response"]
            for item in resp.get("items", []):
                surveys = item.get("surveys", [])
                images  = item.get("imageInfos", [])
                reviews.append({
                    "user_id":     uid,
                    "provider_id": pid,
                    "review_id":   item.get("id", ""),
                    "rating":      item.get("rating", ""),
                    "content":     (item.get("content", "") or "").replace("\n", " ").replace("\r", ""),
                    "created_at":  item.get("createdAt", ""),
                    "survey_tags": "|".join(s.get("text", "") for s in surveys),
                    "has_image":   len(images) > 0,
                    "image_count": len(images),
                    "reviewer_id": item.get("reviewerInfo", {}).get("id", ""),
                })
            pag = resp.get("pagination", {})
            if pag.get("hasNextPage"):
                cursor = pag.get("nextCursor", "")
                time.sleep(DELAY_DETAIL)
            else:
                break
        if reviews:
            append_rows_to_csv(REVIEWS_FILE, reviews, review_fields)
        time.sleep(DELAY_DETAIL)

        # 3. 포트폴리오
        data = fetch_api(f"/v2/users/{uid}/portfolios", params={"size": 20})
        if data and data.get("code") == 0:
            portfolios = []
            for item in data["response"].get("items", []):
                addr = item.get("addressInfo") or {}
                svc  = item.get("serviceInfo") or {}
                portfolios.append({
                    "user_id":        uid,
                    "provider_id":    pid,
                    "portfolio_id":   item.get("id", ""),
                    "title":          (item.get("title", "") or "").replace("\n", " "),
                    "service_name":   svc.get("name", ""),
                    "service_amount": item.get("serviceAmount", ""),
                    "view_count":     item.get("viewCount", 0),
                    "like_count":     item.get("likeCount", 0),
                    "address1":       addr.get("address1", ""),
                    "address2":       addr.get("address2", ""),
                    "created_at":     item.get("createdAt", ""),
                })
            if portfolios:
                append_rows_to_csv(PORTFOLIOS_FILE, portfolios, portfolio_fields)
        time.sleep(DELAY_DETAIL)

        if (i + 1) % 50 == 0 or i == 0 or (i + 1) == total:
            log(f"  [{i+1}/{total}] ({(i+1)/total*100:.1f}%)")

    log("\n  Phase B 완료!")
    for f in [REVIEW_TAGS_FILE, REVIEWS_FILE, PORTFOLIOS_FILE]:
        if os.path.exists(f):
            size  = os.path.getsize(f) / 1024 / 1024
            lines = sum(1 for _ in open(f, encoding="utf-8-sig")) - 1
            log(f"  📄 {f}: {lines}행, {size:.1f}MB")


# ============================================================
# 실행
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="숨고 크롤러 (카테고리별 수집)")
    parser.add_argument("--phase", choices=["a", "b", "all"], default="all")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    log(f"\n{'='*60}")
    log(f"숨고 크롤링: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Phase {args.phase.upper()} {'(TEST)' if args.test else ''}")
    log(f"{'='*60}")

    if args.phase in ("a", "all"):
        phase_a(test_mode=args.test)

    if args.phase in ("b", "all"):
        phase_b(test_mode=args.test)

    log(f"\n완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()