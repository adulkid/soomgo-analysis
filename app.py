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

# ── 보라색 계열 팔레트
C1 = "#4C1D95"
C2 = "#6D28D9"
C3 = "#7C3AED"
C4 = "#8B5CF6"
C5 = "#A78BFA"
C6 = "#C4B5FD"

PRIMARY   = C3
SECONDARY = C5
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
total_hired   = pros['hired_count'].sum()
top1_pct      = pros.nlargest(int(len(pros)*0.01), 'hired_count')['hired_count'].sum() / total_hired * 100
top10_pct     = pros.nlargest(int(len(pros)*0.1),  'hired_count')['hired_count'].sum() / total_hired * 100
bottom90_pct  = 100 - top10_pct
high_rating_pct = (tags['avg_rating'] >= 4.5).sum() / len(tags) * 100
no_review_pct   = (tags['avg_rating'] == 0).sum() / len(tags) * 100

with st.sidebar:
    st.markdown(f"### 📊 숨고 플랫폼 분석")
    st.markdown("---")

    st.markdown("**분석 목적**")
    st.markdown("연결의 양과 질을 진단하여\n구조적 문제와 개선 방향 제시")
    st.markdown("---")

    st.markdown("**데이터 현황**")
    st.markdown(f"""
| 항목 | 수치 |
|------|------|
| 고수 | 27,200명 |
| 카테고리 | 490개 |
| 리뷰 | 107,000건 |
| 수집일 | 2026.03.30 |
""")
    st.markdown("---")

    st.markdown("**분석 한계**")
    limits = [
        ("비활성 고수 미포함", "활성 상위 고수 기준 수집"),
        ("리뷰 평점 신뢰 한계", "긍정 편향 심해 단독 지표 활용 어려움"),
        ("가격 데이터 제외", "포트폴리오 가격 품질 부족"),
        ("내부 데이터 미확보", "견적 요청 수, 실제 선택율 등 접근 불가"),
    ]
    for title, desc in limits:
        st.markdown(f"**· {title}**")
        st.caption(desc)

    st.markdown("---")
    st.markdown("**분석자**")
    st.markdown("찬우 | 개인 프로젝트 2026.04")
    st.markdown("[GitHub](https://github.com/adulkid/soomgo-analysis)")

# ── 메인 제목
st.title("숨고(Soomgo) 플랫폼 분석")
st.markdown("##### 양면 플랫폼 구조 관점에서 바라본 연결의 질 진단")
st.markdown("---")

# ── KPI 카드
col1, col2, col3, col4 = st.columns(4)

kpi_style = f"""
background: white;
border: 1px solid #E5E7EB;
border-top: 4px solid {PRIMARY};
border-radius: 8px;
padding: 1.2rem;
text-align: center;
"""

with col1:
    st.markdown(f"""
<div style='{kpi_style}'>
<div style='font-size:0.85rem; color:#6B7280;'>분석 고수 수</div>
<div style='font-size:2rem; font-weight:700; color:#1F2937;'>{len(pros):,}명</div>
</div>
""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
<div style='{kpi_style}'>
<div style='font-size:0.85rem; color:#6B7280;'>상위 1% 고용 비중</div>
<div style='font-size:2rem; font-weight:700; color:{PRIMARY};'>{top1_pct:.1f}%</div>
<div style='font-size:0.8rem; color:#EF4444;'>전체 고용의 {top1_pct:.2f} 독식</div>
</div>
""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
<div style='{kpi_style}'>
<div style='font-size:0.85rem; color:#6B7280;'>평점 4.5점 이상 비율</div>
<div style='font-size:2rem; font-weight:700; color:{PRIMARY};'>{high_rating_pct:.1f}%</div>
<div style='font-size:0.8rem; color:#EF4444;'>평점 변별력 부족</div>
</div>
""", unsafe_allow_html=True)

with col4:
    st.markdown(f"""
<div style='{kpi_style}'>
<div style='font-size:0.85rem; color:#6B7280;'>리뷰 없는 고수</div>
<div style='font-size:2rem; font-weight:700; color:{PRIMARY};'>{no_review_pct:.1f}%</div>
<div style='font-size:0.8rem; color:#EF4444;'>유령 고수 비율 높음</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── 연결의 양
st.markdown("## 연결의 양 (Volume)")

pro_count = pros.groupby('main_service')['user_id'].count().reset_index()
pro_count.columns = ['main_service', 'pro_count']
pro_count = pro_count.sort_values('pro_count', ascending=False).reset_index(drop=True)

# row 1
col_cat1, col_cat2 = st.columns(2)

with col_cat1:
    import plotly.graph_objects as go

    def get_tier(count):
        if count >= 150:
            return C2
        elif count >= 50:
            return C4
        else:
            return C6

    pro_count['color'] = pro_count['pro_count'].apply(get_tier)

    fig1 = px.bar(pro_count, x=pro_count.index, y='pro_count',
                  hover_data=['main_service'],
                  title='카테고리별 고수 수 분포 (490개)',
                  labels={'pro_count': '고수 수', 'index': '카테고리 순위'})
    fig1.update_traces(marker_color=pro_count['color'].tolist(), showlegend=False)

    for color, name in [
        (C2, '상위권 (150명↑)'),
        (C4, '중간권 (50~150명)'),
        (C6, '하위권 (50명↓)')
    ]:
        fig1.add_trace(go.Bar(x=[None], y=[None], marker_color=color, name=name, showlegend=True))

    fig1.update_xaxes(showticklabels=False)
    fig1.update_layout(
        plot_bgcolor='white', paper_bgcolor='white', height=400,
        legend=dict(title='구간', orientation='v')
    )
    st.plotly_chart(fig1, use_container_width=True)
    st.caption("3 계층으로 나뉘는 고수 분포 — 상위층 / 중간층 / 하위층")

with col_cat2:
    fig1_top = px.bar(
        pro_count.head(20),
        x='main_service', y='pro_count',
        title='고수 수 상위 20개 카테고리',
        labels={'pro_count': '고수 수', 'main_service': '카테고리'},
        color_discrete_sequence=[C3],
        text='pro_count'
    )
    fig1_top.update_traces(textposition='outside')
    fig1_top.update_xaxes(tickangle=-30)
    fig1_top.update_layout(plot_bgcolor='white', paper_bgcolor='white', height=400,yaxis=dict(range=[0, 450]))
    st.plotly_chart(fig1_top, use_container_width=True)
    st.caption("보컬 레슨, 영어 과외 등 교육·생활 카테고리에 고수가 집중")

# row 2
hired_mean   = pros.groupby('main_service')['hired_count'].mean().reset_index()
hired_mean.columns = ['main_service', 'avg_hired_count']
cat_combined = pd.merge(pro_count, hired_mean, on='main_service')
cat_combined['demand_supply_ratio'] = cat_combined['avg_hired_count'] / cat_combined['pro_count']
cat_combined = cat_combined.sort_values('demand_supply_ratio', ascending=False)

col_dsr, col_top = st.columns(2)

with col_dsr:
    fig2 = px.bar(
        cat_combined.head(20),
        x='main_service', y='demand_supply_ratio',
        hover_name='main_service',
        title='고수 1명당 평균 고용횟수 (상위 20개)',
        labels={'demand_supply_ratio': '고수 1명당 평균 고용횟수', 'main_service': '카테고리'},
        color_discrete_sequence=[C4],
        text=cat_combined.head(20)['demand_supply_ratio'].round(1)
    )
    fig2.update_traces(textposition='outside')
    fig2.update_xaxes(tickangle=-30)
    fig2.update_layout(plot_bgcolor='white', paper_bgcolor='white', height=400,yaxis=dict(range=[0, 350]))
    st.plotly_chart(fig2, use_container_width=True)
    st.caption("고수 수와 수요가 불균형을 이루는 카테고리 존재")

with col_top:
    labels = [
        f'상위 1%\n({int(len(pros)*0.01):,}명)',
        f'상위 2~10%\n({int(len(pros)*0.09):,}명)',
        f'하위 90%\n({int(len(pros)*0.9):,}명)'
    ]
    values = [top1_pct, top10_pct - top1_pct, bottom90_pct]
    texts  = [f'{top1_pct:.1f}%', f'{top10_pct-top1_pct:.1f}%', f'{bottom90_pct:.1f}%']

    fig3 = go.Figure(go.Bar(
        x=labels,
        y=values,
        text=texts,
        textposition='outside',
        marker_color=[C1, C5, C6],  # 상위 1%만 C1(가장 진함)
        marker_line_width=[3, 0, 0],  # 상위 1%에 테두리
        marker_line_color=[C1, C1, C1],
    ))
    fig3.update_layout(
        title='고용횟수 점유 구조',
        plot_bgcolor='white', paper_bgcolor='white',
        showlegend=False, height=400,
        yaxis=dict(range=[0, 55]),
        xaxis_title='', yaxis_title='고용 비중 (%)'
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("상위 1%(272명)가 전체 고용의 42% 독식 — 극단적 편중 구조")

st.markdown("---")

# ── 연결의 질
st.markdown("## 연결의 질 (Quality)")

# row 1
col_q1, col_q2 = st.columns(2)

with col_q1:
    tags_filtered = tags[tags['avg_rating'] > 0].copy()
    tags_filtered['color'] = tags_filtered['avg_rating'].apply(
        lambda x: C1 if x == 5.0 else C5
    )

    fig4 = px.histogram(tags_filtered, x='avg_rating',
                        title='고수별 평균 평점 분포 (리뷰 있는 고수)',
                        labels={'avg_rating': '평균 평점', 'count': '고수 수'},
                        color='color',
                        color_discrete_map={C1: C1, C5: C5}, 
                        )
    fig4.update_layout(
        plot_bgcolor='white', paper_bgcolor='white', height=400,
        showlegend=False
    )
    st.plotly_chart(fig4, use_container_width=True)
    st.caption(f"평점 4.5점 이상: {high_rating_pct:.1f}% / 평점 1~3점: 0.75% — 변별력이 낮은 리뷰 시스템")

with col_q2:
    merged = pd.merge(
        pros[['user_id', 'hired_count']],
        tags[tags['avg_rating'] > 0][['user_id', 'avg_rating', 'total_review_count']],
        on='user_id'
    )
    # 이상치 제거 (리뷰 수 상위 1% 제외)
    q99 = merged['total_review_count'].quantile(0.99)
    merged_filtered = merged[merged['total_review_count'] <= q99]

    fig_scatter = px.scatter(
        merged_filtered,
        x='total_review_count',
        y='avg_rating',
        title='리뷰 수 vs 평균 평점 (상위 1% 제외)',
        labels={'total_review_count': '리뷰 수', 'avg_rating': '평균 평점'},
        color='hired_count',
        color_continuous_scale=[[0, C6], [0.5, C3], [1.0, C1]],
        opacity=0.6,
    )
    fig_scatter.update_layout(plot_bgcolor='white', paper_bgcolor='white', height=400)
    st.plotly_chart(fig_scatter, use_container_width=True)
    st.caption("대부분 고수의 평점이 5점에 집중 — 리뷰 수와 무관하게 평점 변별력 없음")

# row 2
st.markdown("#### 리뷰 텍스트 마이닝 — 평점별 키워드 비교")

col_wc1, col_wc2 = st.columns(2)
with col_wc1:
    st.markdown("**낮은 평점 (1~3점)**")
    wc_low = WordCloud(font_path=FONT_PATH, width=600, height=350,
                       background_color='white', colormap='Reds').generate_from_frequencies(low_counter)
    fig_wc1, ax1 = plt.subplots(figsize=(6, 3.5))
    ax1.imshow(wc_low); ax1.axis('off')
    st.pyplot(fig_wc1)
    st.caption("불만 키워드: 작업·견적·비용(서비스 품질) + 시간·전화·연락(신뢰 문제)")

with col_wc2:
    st.markdown("**높은 평점 (4~5점)**")
    wc_high = WordCloud(font_path=FONT_PATH, width=600, height=350,
                        background_color='white', colormap='Blues').generate_from_frequencies(high_counter)
    fig_wc2, ax2 = plt.subplots(figsize=(6, 3.5))
    ax2.imshow(wc_high); ax2.axis('off')
    st.pyplot(fig_wc2)
    st.caption("만족 키워드: 빠르·진행·시공(서비스 품질) + 친절·감사·상담(응대 태도)")

st.markdown("---")

# ── 구조적 문제
st.markdown("## 구조적 문제")

col_corr, col_insight = st.columns([1.5, 1])

with col_corr:
    corr_cols = ['career', 'review_count', 'hired_count', 'review_rate', 'avg_response_time']
    corr = pros[corr_cols].corr()
    corr.index   = ['경력', '리뷰 수', '고용횟수', '평점', '평균 응답시간']
    corr.columns = ['경력', '리뷰 수', '고용횟수', '평점', '평균 응답시간']
    fig5 = px.imshow(corr, text_auto='.2f',
                     color_continuous_scale='RdBu_r',
                     title='변수 간 상관관계 히트맵')
    fig5.update_layout(height=420, margin=dict(l=20, r=20, t=60, b=20))
    fig5.update_traces(zmin=-1, zmax=1)
    st.plotly_chart(fig5, use_container_width=True)
    st.caption("리뷰 수(0.83)만 고용횟수와 높은 상관 — 개인 노력 변수는 거의 무관")

with col_insight:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(f"""
<div style='background:{ACCENT}; border-left: 4px solid {PRIMARY};
     padding: 1.5rem; border-radius: 8px;'>
<h4 style='color:{PRIMARY}; margin-top:0;'>💡 핵심 인사이트</h4>
<h3 style='color:#1F2937;'>승자독식 구조의 고용시장</h3>
<p style='color:#374151; line-height:1.8;'>
고용이 상위 소수 고수에게 집중되어 있고,<br>
이를 결정하는 핵심 변수는 <b>리뷰 수(0.83)</b>다.<br><br>
경력, 응답시간, 평점 등<br>
<b>개인이 노력으로 바꿀 수 있는 변수</b>는<br>
고용횟수와 거의 무관하다.<br><br>
리뷰-고용 순환 구조가 고착화되어<br>
신규 고수의 진입 장벽이 구조적으로 높다.
</p>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# ── 제언
st.markdown("## 제언")
st.markdown("##### 플랫폼이 수동적 연결자에서 능동적 생태계 설계자로 역할을 전환해야 한다.")

st.markdown("")

col1, col2, col3 = st.columns(3)
card_style = f"background:{ACCENT}; border-left: 4px solid {PRIMARY}; padding: 1.2rem; border-radius: 8px; min-height: 210px; height: auto;"

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
고수 1인당 평균 고용횟수 기반 공급 부족 카테고리 식별 → 전문가 능동적 유치<br><br>
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