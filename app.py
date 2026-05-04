import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import platform
import matplotlib.pyplot as plt
import pickle
from wordcloud import WordCloud

# ── 페이지 설정
st.set_page_config(
    page_title="숨고 플랫폼 분석",
    page_icon="🔍",
    layout="wide"
)

# ── 숨고 브랜드 컬러
PRIMARY   = "#7C3AED"
SECONDARY = "#A78BFA"
ACCENT    = "#EDE9FE"
GRAY      = "#9CA3AF"

# ── 커스텀 CSS
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h2 { margin-top: 2rem !important; }
    .stCaption { color: #6B7280; font-size: 0.82rem; }
</style>
""", unsafe_allow_html=True)

# ── 폰트 설정
if platform.system() == 'Darwin':
    FONT_PATH = '/System/Library/Fonts/AppleSDGothicNeo.ttc'
    plt.rcParams['font.family'] = 'AppleGothic'
else:
    FONT_PATH = 'fonts/NanumGothic-Regular.ttf'
    plt.rcParams['font.family'] = 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False

# ── 데이터 로드
@st.cache_data
def load_data():
    pros    = pd.read_csv('soomgo_pros_f.csv')
    tags    = pd.read_csv('soomgo_review_tags_f.csv')
    reviews = pd.read_csv('soomgo_reviews_clean.csv')
    pros['avg_response_time'] = pros['avg_response_time'].replace(-1, np.nan)
    pros['is_ambassador']     = pros['is_ambassador'].astype(int)
    reviews = reviews.drop_duplicates(subset=['review_id'])
    return pros, tags, reviews

pros, tags, reviews = load_data()

# ── 텍스트 마이닝 캐싱
@st.cache_data
def get_word_counters():
    with open('word_counters.pkl', 'rb') as f:
        return pickle.load(f)

low_counter, high_counter = get_word_counters()

# ── KPI 계산
total_hired  = pros['hired_count'].sum()
top1_pct     = pros.nlargest(int(len(pros)*0.01), 'hired_count')['hired_count'].sum() / total_hired * 100
top10_pct    = pros.nlargest(int(len(pros)*0.1),  'hired_count')['hired_count'].sum() / total_hired * 100
bottom90_pct = 100 - top10_pct
rating_5_pct  = (tags['avg_rating'] == 5).sum() / len(tags) * 100
no_review_pct = (tags['avg_rating'] == 0).sum() / len(tags) * 100

# ── 사이드바
with st.sidebar:
    st.markdown("### 📊 숨고 플랫폼 분석")
    st.markdown("---")
    st.markdown("**분석 개요**")
    st.markdown("숨고 플랫폼의 연결 구조를 양(Volume)과 질(Quality) 두 축으로 진단한다.")
    st.markdown("---")
    st.markdown("**데이터 출처**")
    st.markdown("- 숨고 내부 API 크롤링\n- 수집 기준: 2026.03.30\n- 고수 27,200명 / 리뷰 107,000건")
    st.markdown("---")
    st.markdown("**분석자**")
    st.markdown("찬우 | 개인 프로젝트 2026.04")

# ── 메인 제목
st.title("숨고(Soomgo) 플랫폼 분석")
st.markdown("##### 양면 플랫폼 구조 관점에서 바라본 연결의 질 진단")
st.markdown("---")

# ── KPI 카드
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("분석 고수 수", f"{len(pros):,}명")
with col2:
    st.metric("상위 1% 고용 비중", f"{top1_pct:.1f}%", "상위 1%가 전체 고용의 42% 독식", delta_color="inverse")
with col3:
    st.metric("5점 만점 비율", f"{rating_5_pct:.1f}%", "평점 변별력 부족", delta_color="inverse")
with col4:
    st.metric("리뷰 없는 고수", f"{no_review_pct:.1f}%", "신규 고수 진입 장벽", delta_color="inverse")

st.markdown("---")

# ── 연결의 양
st.markdown("## 📦 연결의 양 (Volume)")

pro_count = pros.groupby('main_service')['user_id'].count().reset_index()
pro_count.columns = ['main_service', 'pro_count']
pro_count = pro_count.sort_values('pro_count', ascending=False).reset_index(drop=True)

fig1 = px.bar(pro_count, x=pro_count.index, y='pro_count',
              hover_data=['main_service'],
              title='카테고리별 고수 수 분포 (490개)',
              labels={'pro_count': '고수 수', 'index': '카테고리 순위'},
              color_discrete_sequence=[PRIMARY])
fig1.update_xaxes(showticklabels=False)
fig1.update_layout(plot_bgcolor='white', paper_bgcolor='white')
st.plotly_chart(fig1, use_container_width=True)
st.caption("상위 집중 / 중간 균일 / 하위 극소 — 세 구간으로 나뉘는 고수 분포")

hired_mean   = pros.groupby('main_service')['hired_count'].mean().reset_index()
hired_mean.columns = ['main_service', 'avg_hired_count']
cat_combined = pd.merge(pro_count, hired_mean, on='main_service')
cat_combined['demand_supply_ratio'] = cat_combined['avg_hired_count'] / cat_combined['pro_count']
cat_combined = cat_combined.sort_values('demand_supply_ratio', ascending=False)

fig2 = px.bar(cat_combined.head(50), x='main_service', y='demand_supply_ratio',
              hover_name='main_service',
              title='고수 1명당 평균 고용횟수 — demand_supply_ratio (상위 50개)',
              labels={'demand_supply_ratio': '고수 1명당 평균 고용횟수', 'main_service': '카테고리'},
              color_discrete_sequence=[SECONDARY])
fig2.update_xaxes(showticklabels=False)
fig2.update_layout(plot_bgcolor='white', paper_bgcolor='white')
st.plotly_chart(fig2, use_container_width=True)
st.caption("고수 수와 수요가 불균형을 이루는 카테고리 존재 — 공급 부족 카테고리 타깃 유치 근거")

st.markdown("---")

# ── 연결의 질
st.markdown("## 🔍 연결의 질 (Quality)")

fig4 = px.histogram(tags[tags['avg_rating'] > 0], x='avg_rating',
                    title='고수별 평균 평점 분포 (리뷰 있는 고수)',
                    labels={'avg_rating': '평균 평점', 'count': '고수 수'},
                    color_discrete_sequence=[PRIMARY])
fig4.update_layout(plot_bgcolor='white', paper_bgcolor='white')
st.plotly_chart(fig4, use_container_width=True)
st.caption(f"평점 5점: {rating_5_pct:.1f}% / 평점 1~3점: 0.75% — 변별력이 낮은 리뷰 시스템")

st.markdown("#### 리뷰 텍스트 마이닝 — 평점별 키워드 비교")
with st.spinner('텍스트 분석 중... (최초 1회 소요)'):
    low_counter, high_counter = get_word_counters(reviews)

col_wc1, col_wc2 = st.columns(2)
with col_wc1:
    st.markdown("**낮은 평점 (1~3점)**")
    wc_low = WordCloud(font_path=FONT_PATH, width=600, height=350,
                       background_color='white', colormap='Reds').generate_from_frequencies(low_counter)
    fig_wc1, ax1 = plt.subplots(figsize=(6, 3.5))
    ax1.imshow(wc_low); ax1.axis('off')
    st.pyplot(fig_wc1)
    st.caption("연락, 시간, 약속, 추가금 — 신뢰 문제가 핵심")

with col_wc2:
    st.markdown("**높은 평점 (4~5점)**")
    wc_high = WordCloud(font_path=FONT_PATH, width=600, height=350,
                        background_color='white', colormap='Blues').generate_from_frequencies(high_counter)
    fig_wc2, ax2 = plt.subplots(figsize=(6, 3.5))
    ax2.imshow(wc_high); ax2.axis('off')
    st.pyplot(fig_wc2)
    st.caption("친절, 빠르, 깔끔, 만족 — 응대 태도와 결과물 품질")

st.markdown("---")

# ── 구조적 문제
st.markdown("## ⚠️ 구조적 문제")

col_pie, col_corr = st.columns(2)
with col_pie:
    fig3 = px.pie(
        values=[top1_pct, top10_pct - top1_pct, bottom90_pct],
        names=['상위 1%', '상위 2~10%', '하위 90%'],
        title='고용횟수 점유 구조',
        color_discrete_sequence=[PRIMARY, SECONDARY, GRAY])
    fig3.update_layout(height=420)
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("상위 1%(272명)가 전체 고용의 42% 독식 — 극단적 편중 구조")

with col_corr:
    corr_cols = ['career', 'review_count', 'hired_count', 'review_rate', 'avg_response_time']
    corr = pros[corr_cols].corr()
    fig5 = px.imshow(corr, text_auto='.2f',
                     color_continuous_scale='RdBu_r',
                     title='변수 간 상관관계 히트맵')
    fig5.update_layout(height=420, margin=dict(l=20, r=20, t=60, b=20))
    st.plotly_chart(fig5, use_container_width=True)
    st.caption("review_count(0.83)만 hired_count와 높은 상관 — 개인 노력 변수는 거의 무관")

st.markdown("---")

# ── 제언
st.markdown("## 💡 제언")
st.markdown("##### 플랫폼이 수동적 연결자에서 능동적 생태계 설계자로 역할을 전환해야 한다.")

st.info("""
**핵심 인사이트: 플랫폼이 고여있다**

리뷰-고용 순환 구조가 고착화되어 신규 고수의 진입 장벽이 구조적으로 높다.  
개인의 노력(경력, 응답시간, 평점)만으로는 이 구조를 극복하기 어렵다.
""")

st.markdown("")

col1, col2, col3 = st.columns(3)
card_style = f"background:{ACCENT}; border-left: 4px solid {PRIMARY}; padding: 1.2rem; border-radius: 8px; height: 210px;"

with col1:
    st.markdown(f"""
<div style='{card_style}'>
<b>🎯 신규 고수 온보딩 지원</b><br><br>
수수료 감면 + 성실 활동 기준 충족 시 추가 혜택<br><br>
• 응답시간 기준 이내 유지<br>
• 견적 발송 N건 이상<br>
• 첫 거래 완료
</div>
""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
<div style='{card_style}'>
<b>📍 공급 부족 카테고리 타깃 유치</b><br><br>
demand_supply_ratio 기반 공급 부족 카테고리 식별 → 전문가 능동적 유치<br><br>
• 플랫폼이 먼저 컨택<br>
• 초기 정착 지원
</div>
""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
<div style='{card_style}'>
<b>💰 신규 고수 선택 소비자 유인</b><br><br>
플랫폼 검증 배지 + 첫 거래 할인으로 소비자 리스크·비용 절감<br><br>
• 숨고 인증 신규 고수 배지<br>
• 첫 거래 가격 할인
</div>
""", unsafe_allow_html=True)

st.markdown("---")
st.caption("본 분석은 공개 데이터 기반 개인 프로젝트입니다. 2026.04 | 숨고 플랫폼 분석")