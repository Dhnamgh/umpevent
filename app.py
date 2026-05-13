import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="UMP Dashboard", layout="wide")

# =========================
# LOAD DATA
# =========================
@st.cache_data(ttl=600)
def load_data():
    url = st.secrets["data"]["csv_url"]

    df = pd.read_csv(url)

    df = df.rename(columns={
        "Tên sự kiện": "event",
        "Đơn vị phụ trách/ tổ chức": "donvi",
        "Ngày tổ chức": "start",
        "Ngày kết thúc": "end",
        "Địa điểm tổ chức": "location"
    })

    df["start"] = pd.to_datetime(df["start"], errors="coerce")
    df["end"] = pd.to_datetime(df["end"], errors="coerce")

    df["end"] = df["end"].fillna(df["start"])

    df["month"] = df["start"].dt.month
    df["year"] = df["start"].dt.year

    return df

df = load_data()

# =========================
# CHỌN ĐƠN VỊ
# =========================
donvi_list = sorted(df["donvi"].dropna().unique())

# thêm option toàn trường
options = ["Toàn trường"] + list(donvi_list)

selected = st.sidebar.multiselect(
    "Chọn đơn vị",
    options,
    default=["Phòng Hành chính Tổng hợp"]
)

# xử lý logic
if "Toàn trường" in selected or len(selected) == 0:
    df_f = df.copy()
else:
    df_f = df[df["donvi"].isin(selected)]

# =========================
# TAB
# =========================
tab1, tab2 = st.tabs(["📊 Dashboard", "📈 Tổng hợp"])

# =========================
# TAB 1 - DASHBOARD
# =========================
with tab1:
    st.title("📊 Dashboard Quản lý sự kiện UMP")

    # KPI
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng sự kiện", len(df_f))
    c2.metric("Số đơn vị", df_f["donvi"].nunique())
    c3.metric("Địa điểm", df_f["location"].nunique())

    st.divider()

    # Table
    st.subheader("📋 Dữ liệu chi tiết")
    st.dataframe(df_f, use_container_width=True)

    # Gantt
    st.subheader("📅 Biểu đồ Gantt")

    df_g = df_f.dropna(subset=["start"])

    fig = px.timeline(
        df_g,
        x_start="start",
        x_end="end",
        y="event",
        color="donvi",
        hover_data=["location"]
    )

    fig.update_yaxes(autorange="reversed")

    st.plotly_chart(fig, use_container_width=True)

    # Summary
    st.subheader("📊 Số sự kiện theo đơn vị")

    summary = df_f.groupby("donvi").size().reset_index(name="count")
    fig2 = px.bar(summary, x="donvi", y="count")
    st.plotly_chart(fig2, use_container_width=True)

# =========================
# TAB 2 - TỔNG HỢP
# =========================
with tab2:
    st.title("📊 Báo cáo tổng hợp")

    today = datetime.today()
    current_month = today.month
    current_year = today.year

    # tháng hiện tại (tính đến hôm nay)
    df_month = df[
        (df["start"].dt.year == current_year) &
        (df["start"].dt.month == current_month) &
        (df["start"] <= today)
    ]

    # YTD (đến hôm nay)
    df_ytd = df[
        (df["start"].dt.year == current_year) &
        (df["start"] <= today)
    ]

    # ----- THÁNG -----
    st.subheader(f"📅 Tháng {current_month}/{current_year}")

    c1, c2 = st.columns(2)
    c1.metric("Số sự kiện", len(df_month))
    c2.metric("Số đơn vị", df_month["donvi"].nunique())

    summary_month = df_month.groupby("donvi").size().reset_index(name="count")
    st.bar_chart(summary_month.set_index("donvi"))

    st.divider()

    # ----- YTD -----
    st.subheader(f"📅 Từ đầu năm đến hiện tại")

    c1, c2 = st.columns(2)
    c1.metric("Số sự kiện", len(df_ytd))
    c2.metric("Số đơn vị", df_ytd["donvi"].nunique())

    summary_ytd = df_ytd.groupby("donvi").size().reset_index(name="count")
    st.bar_chart(summary_ytd.set_index("donvi"))

# =========================
# FOOTER
# =========================
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:gray;'>© Bản quyền thuộc về TS. Đào Hồng Nam</div>",
    unsafe_allow_html=True
)
