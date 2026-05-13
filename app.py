import streamlit as st
import pandas as pd
import plotly.express as px

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

    # đổi tên cột cho dễ dùng
    df = df.rename(columns={
        "Tên sự kiện": "event",
        "Đơn vị phụ trách/ tổ chức": "donvi",
        "Ngày tổ chức": "start",
        "Ngày kết thúc": "end",
        "Địa điểm tổ chức": "location"
    })

    # convert date
    df["start"] = pd.to_datetime(df["start"], errors="coerce")
    df["end"] = pd.to_datetime(df["end"], errors="coerce")

    # nếu thiếu end thì lấy start
    df["end"] = df["end"].fillna(df["start"])

    return df

df = load_data()

# =========================
# SIDEBAR FILTER
# =========================
st.sidebar.title("Bộ lọc")

donvi_list = df["donvi"].dropna().unique()

chon_donvi = st.sidebar.multiselect(
    "Chọn đơn vị",
    donvi_list,
    default=donvi_list
)

df_f = df[df["donvi"].isin(chon_donvi)]

# =========================
# DASHBOARD
# =========================
st.title("📊 Dashboard Quản lý sự kiện UMP")

# KPI
c1, c2, c3 = st.columns(3)

c1.metric("Tổng sự kiện", len(df_f))
c2.metric("Số đơn vị", df_f["donvi"].nunique())
c3.metric("Địa điểm", df_f["location"].nunique())

st.divider()

# TABLE
st.subheader("📋 Dữ liệu chi tiết")
st.dataframe(df_f, use_container_width=True)

# =========================
# GANTT CHART
# =========================
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

# =========================
# SUMMARY CHART
# =========================
st.subheader("📊 Số lượng sự kiện theo đơn vị")

summary = df_f.groupby("donvi").size().reset_index(name="count")

fig2 = px.bar(summary, x="donvi", y="count")

st.plotly_chart(fig2, use_container_width=True)
