import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

# ================= CSS =================
st.markdown("""
<style>
section[data-testid="stSidebar"] {
    width: 360px !important;
}

.menu-btn {
    background-color: #1976d2;
    color: white;
    padding: 10px;
    border-radius: 6px;
    margin-bottom: 8px;
    text-align: center;
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

# ================= MENU SIDEBAR =================
st.sidebar.title("📋 MENU")

menu = st.sidebar.radio(
    "",
    ["Dashboard", "Tổng hợp", "Trợ giúp", "Phê duyệt SK", "Liên hệ"]
)

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

    df_year = df[df["start"].dt.year == today.year]
    df_month = df_year[df_year["start"].dt.month == today.month]
    df_week = df_year[df_year["start"] >= today - timedelta(days=7)]

    # KPI
    c1, c2, c3 = st.columns(3)
    c1.metric("Tuần", len(df_week))
    c2.metric("Tháng", len(df_month))
    c3.metric("Năm", len(df_year))

    # danh sách tháng
    st.subheader("📅 Sự kiện trong tháng")
    st.dataframe(df_month.sort_values("start"), use_container_width=True)

    # timeline chỉ năm hiện hành
    st.subheader("📈 Timeline năm hiện hành")
    fig = px.timeline(
        df_year,
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

    df_year = df[df["start"].dt.year == today.year]
    df_month = df_year[df_year["start"].dt.month == today.month]

    st.metric("Tháng", len(df_month))
    st.metric("Năm", len(df_year))

# ================= TRỢ GIÚP =================
elif menu == "Trợ giúp":

    st.title("🤖 Trợ giúp")

    q = st.text_input("Nhập câu hỏi")

    if q:
        q = q.lower()

        if "tuần" in q:
            res = df[df["start"] >= today - timedelta(days=7)]
            st.dataframe(res)

        elif "tháng" in q:
            res = df[
                (df["start"].dt.month == today.month) &
                (df["start"].dt.year == today.year)
            ]
            st.dataframe(res)

        elif "mới" in q:
            st.dataframe(df.sort_values("start", ascending=False).head(5))

        elif "hỗ trợ" in q:
            support_df = df[df["donvi"] == "Phòng Hành chính Tổng hợp"]

            st.dataframe(support_df)

            if "support" in support_df.columns:
                st.subheader("🔧 Nội dung hỗ trợ")
                for s in support_df["support"].dropna().unique():
                    st.markdown(f"- {s}")

        elif "đông" in q:
            if "people" in df.columns:
                st.dataframe(df[df["people"] > 100])

        else:
            st.warning("Chưa hiểu câu hỏi")

# ================= PHÊ DUYỆT =================
elif menu == "Phê duyệt SK":

    st.title("🔐 Phê duyệt sự kiện")

    password = st.text_input("Nhập mật khẩu", type="password")

    if "auth" not in st.session_state:
        st.session_state["auth"] = False

    if password:
        if password == st.secrets["auth"]["password"]:
            st.session_state["auth"] = True
        else:
            st.error("Sai mật khẩu")

    if st.session_state["auth"]:
        st.success("Đã đăng nhập")

        df["status"] = df.get("status", "Chờ")

        choice = st.selectbox("Chọn trạng thái", ["Thống nhất", "Chưa thống nhất", "Cần liên hệ"])

        event = st.selectbox("Chọn sự kiện", df["event"])

        if st.button("Cập nhật"):
            df.loc[df["event"] == event, "status"] = choice
            st.success(f"Đã cập nhật: {event} → {choice}")

        st.dataframe(df[["event", "status"]])

# ================= LIÊN HỆ =================
elif menu == "Liên hệ":

    st.title("📞 Liên hệ")

    st.markdown("""
**Phòng Hành chính Tổng hợp**

Địa chỉ: 217 Hồng Bàng, Phường Chợ Lớn, TP.HCM  

ĐT: (+84-28) 3855 8411 - 3853 7949 - 3855 5780  

Email: <a href="mailto:hanhchinh@ump.edu.vn">hanhchinh@ump.edu.vn</a>
""", unsafe_allow_html=True)

# ================= FOOTER =================
st.markdown("---")
st.markdown("<center>© TS. Đào Hồng Nam</center>", unsafe_allow_html=True)
``
