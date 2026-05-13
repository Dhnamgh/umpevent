import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

# ================= CSS =================
st.markdown("""
<style>
section[data-testid="stSidebar"] {
    width: 320px !important;
}
.menu-btn {
    background-color: #1976d2;
    color: white;
    padding: 10px;
    border-radius: 6px;
    text-align: center;
    margin-right: 10px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ================= LOAD =================
@st.cache_data(ttl=600)
def load_data():
    url = st.secrets["data"]["csv_url"]
    df = pd.read_csv(url)

    df = df.rename(columns={
        "Tên sự kiện": "event",
        "Đơn vị phụ trách/ tổ chức": "donvi",
        "Ngày tổ chức": "start",
        "Ngày kết thúc": "end",
        "Địa điểm tổ chức": "location",
        "Số lượng": "people",
        "Hỗ trợ": "support"
    })

    df["start"] = pd.to_datetime(df["start"], errors="coerce")
    df["end"] = pd.to_datetime(df["end"], errors="coerce")
    df["end"] = df["end"].fillna(df["start"])

    return df

df = load_data()

today = datetime.today()

# ================= MENU NGANG =================
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("📊 Dashboard"):
        st.session_state["menu"] = "Dashboard"
with col2:
    if st.button("📈 Tổng hợp"):
        st.session_state["menu"] = "Tổng hợp"
with col3:
    if st.button("🤖 Trợ giúp"):
        st.session_state["menu"] = "Trợ giúp"
with col4:
    if st.button("📞 Liên hệ"):
        st.session_state["menu"] = "Liên hệ"

menu = st.session_state.get("menu", "Dashboard")

# ================= FILTER =================
donvi_list = sorted(df["donvi"].dropna().unique())
options = ["Toàn trường"] + list(donvi_list)

selected = st.sidebar.multiselect(
    "Chọn đơn vị",
    options,
    default=["Phòng Hành chính Tổng hợp"]
)

if "Toàn trường" in selected or len(selected) == 0:
    df_f = df.copy()
else:
    df_f = df[df["donvi"].isin(selected)]

# ================= DASHBOARD =================
if menu == "Dashboard":

    st.title("📊 Dashboard")

    # ===== KPI =====
    week_start = today - timedelta(days=7)

    df_week = df[df["start"] >= week_start]
    df_month = df[
        (df["start"].dt.month == today.month) &
        (df["start"].dt.year == today.year)
    ]
    df_year = df[df["start"].dt.year == today.year]

    c1, c2, c3 = st.columns(3)
    c1.metric("Trong tuần", len(df_week))
    c2.metric("Trong tháng", len(df_month))
    c3.metric("Trong năm", len(df_year))

    # ===== LIST MONTH =====
    st.subheader("📅 Sự kiện trong tháng")

    df_month_sorted = df_month.sort_values("start")
    st.dataframe(df_month_sorted, use_container_width=True)

    # ===== GANTT =====
    st.subheader("📈 Timeline")

    fig = px.timeline(
        df_f,
        x_start="start",
        x_end="end",
        y="event",
        color="donvi"
    )
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

# ================= TỔNG HỢP =================
elif menu == "Tổng hợp":

    st.title("📊 Tổng hợp")

    df_month = df[
        (df["start"].dt.month == today.month) &
        (df["start"].dt.year == today.year)
    ]

    df_ytd = df[df["start"].dt.year == today.year]

    st.metric("Tháng", len(df_month))
    st.metric("Năm", len(df_ytd))

# ================= TRỢ GIÚP =================
elif menu == "Trợ giúp":

    st.title("🤖 Trợ giúp")

    q = st.text_input("Hỏi:")

    if q:
        q = q.lower()

        # tuần
        if "tuần" in q:
            week = df[
                (df["start"] >= today - timedelta(days=7)) &
                (df["start"] <= today)
            ]
            st.dataframe(week)

        # tháng ✅ FIX
        elif "tháng" in q:
            month = df[
                (df["start"].dt.month == today.month) &
                (df["start"].dt.year == today.year)
            ]
            st.dataframe(month)

        # mới nhất
        elif "mới" in q:
            latest = df.sort_values("start", ascending=False).head(5)
            st.dataframe(latest)

        # hỗ trợ
        elif "hỗ trợ" in q:
            support_df = df[df["donvi"] == "Phòng Hành chính Tổng hợp"]

            st.dataframe(support_df)

            if "support" in support_df.columns:
                st.subheader("🔧 Nội dung hỗ trợ")
                for item in support_df["support"].dropna().unique():
                    st.markdown(f"- {item}")

        # đông người
        elif "đông" in q or "100" in q:
            crowded = df[df["people"] > 100]
            st.dataframe(crowded)

        else:
            st.warning("Chưa hiểu câu hỏi")

# ================= LIÊN HỆ =================
elif menu == "Liên hệ":

    st.title("📞 Liên hệ")

    st.markdown("""
**Phòng Hành chính Tổng hợp**

Địa chỉ: 217 Hồng Bàng, Phường Chợ Lớn, TP. Hồ Chí Minh  

ĐT: (+84-28) 3855 8411 - (+84-28) 3853 7949 - (+84-28) 3855 5780  

Fax: (+84-28) 3855 2304  

Email: <a href="mailto:hanhchinh@ump.edu.vn">hanhchinh@ump.edu.vn</a>
""", unsafe_allow_html=True)

# ================= FOOTER =================
st.markdown("---")
st.markdown(
    "<center>© TS. Đào Hồng Nam</center>",
    unsafe_allow_html=True
)
