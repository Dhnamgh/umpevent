import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
html, body {font-size:16px; color:#000;}
section[data-testid="stSidebar"] {width:360px !important;}
button[kind="primary"] {background-color:#1976d2; color:white;}
</style>
""", unsafe_allow_html=True)

# ================= TITLE =================
st.title("📊 Quản lý sự kiện UMP")

# ================= LOAD =================
@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv(st.secrets["data"]["csv_url"])
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

# ================= MENU =================
menu = st.sidebar.radio(
    "MENU",
    ["Dashboard", "Báo cáo", "Cảnh báo", "Trợ giúp", "Phê duyệt", "Liên hệ"]
)

# ================= FILTER =================
donvi_list = sorted(df["donvi"].dropna().unique())

selected = st.sidebar.multiselect(
    "Chọn đơn vị",
    ["Toàn trường"] + donvi_list,
    default=["Toàn trường"]
)

st.sidebar.write("✅ Đang chọn:", ", ".join(selected))

if "Toàn trường" in selected:
    df_f = df
else:
    df_f = df[df["donvi"].isin(selected)]

# ================= DASHBOARD =================
if menu == "Dashboard":

    st.subheader(f"📅 Lịch toàn trường - Tháng {today.month}/{today.year}")

    st.write("👉 Mặc định hiển thị toàn trường theo tháng hiện hành. Có thể chọn tuần hoặc năm bên dưới.")

    col1, col2, col3 = st.columns(3)

    if "view" not in st.session_state:
        st.session_state["view"] = "Tháng"

    if col1.button("📆 Tuần"):
        st.session_state["view"] = "Tuần"
    if col2.button("📅 Tháng"):
        st.session_state["view"] = "Tháng"
    if col3.button("📊 Năm"):
        st.session_state["view"] = "Năm"

    view = st.session_state["view"]

    df_year = df_f[df_f["start"].dt.year == today.year]
    df_month = df_year[df_year["start"].dt.month == today.month]
    df_week = df_year[(df_year["start"] >= today - timedelta(days=7)) & (df_year["start"] <= today)]

    if view == "Tháng":
        df_view = df_month
    elif view == "Tuần":
        df_view = df_week
    else:
        df_view = df_year

    # KPI đúng
    c1,c2,c3 = st.columns(3)
    c1.metric("Tuần", len(df_week))
    c2.metric("Tháng", len(df_month))
    c3.metric("Năm", len(df_year))

    st.dataframe(df_view.sort_values("start"), use_container_width=True)

    fig = px.timeline(df_year, x_start="start", x_end="end", y="event", color="donvi")
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

# ================= BÁO CÁO =================
elif menu == "Báo cáo":

    mode = st.radio("Chọn báo cáo", ["Tuần", "Tháng", "Năm"], horizontal=True)

    df_year = df_f[df_f["start"].dt.year == today.year]
    df_month = df_year[df_year["start"].dt.month == today.month]
    df_week = df_year[(df_year["start"] >= today - timedelta(days=7)) & (df_year["start"] <= today)]

    if mode == "Tuần":
        data = df_week
    elif mode == "Tháng":
        data = df_month
    else:
        data = df_year

    summary = data.groupby("donvi").size().reset_index(name="count")

    fig = px.bar(summary, x="donvi", y="count", text="count")
    fig.update_traces(textposition='outside')

    st.plotly_chart(fig, use_container_width=True)

# ================= CẢNH BÁO =================
elif menu == "Cảnh báo":

    st.subheader("⚠️ Cảnh báo trùng lịch (Tháng hiện tại + tháng kế tiếp)")

    next_month = today + timedelta(days=30)

    df_check = df[
        (df["start"] >= today) &
        (df["start"] <= next_month)
    ]

    for i in range(len(df_check)):
        for j in range(i+1, len(df_check)):
            if df_check.iloc[i]["start"] == df_check.iloc[j]["start"]:

                t = df_check.iloc[i]["start"].strftime("%H:%M %d/%m/%Y")

                st.warning(f"""
Trùng lịch: {t}  
• {df_check.iloc[i]["event"]} (Địa điểm: {df_check.iloc[i]["location"]})  
• {df_check.iloc[j]["event"]} (Địa điểm: {df_check.iloc[j]["location"]})
""")

# ================= TRỢ GIÚP =================
elif menu == "Trợ giúp":

    st.subheader("🤖 Trợ giúp")
    st.write("👉 Nhập câu hỏi và nhấn Enter")

    q = st.text_input("Nhập câu hỏi:")

    if q:
        q = q.lower()

        df_year = df[df["start"].dt.year == today.year]

        if "tuần" in q:
            res = df_year[(df_year["start"] >= today - timedelta(days=7)) & (df_year["start"] <= today+timedelta(days=7))]
            st.dataframe(res)

        elif "tháng" in q:
            res = df_year[df_year["start"].dt.month == today.month]
            st.dataframe(res)

        elif "năm" in q:
            st.dataframe(df_year)

        elif "hỗ trợ" in q:
            next_month = today + timedelta(days=30)

            res = df[
                (df["start"] >= today) &
                (df["start"] <= next_month)
            ]

            st.dataframe(res)

            if "support" in res.columns:
                st.subheader("🔧 Tổng hợp hỗ trợ")

                summary = res["support"].value_counts().reset_index()
                summary.columns = ["Loại hỗ trợ", "Số lượng"]

                st.table(summary)

        elif "đông" in q:
            st.dataframe(df[df["people"] > 100])

        else:
            st.info("Chưa hiểu câu hỏi")

# ================= PHÊ DUYỆT =================
elif menu == "Phê duyệt":

    st.subheader("📋 Sự kiện cần phê duyệt (tháng hiện hành)")

    df_month = df[df["start"].dt.month == today.month]
    df_pending = df_month[df_month["start"] >= today]

    st.dataframe(df_pending.sort_values("start"), use_container_width=True)

# ================= LIÊN HỆ =================
elif menu == "Liên hệ":

    st.markdown("""
### 📞 Phòng Hành chính Tổng hợp

217 Hồng Bàng, Phường Chợ Lớn, Thành phố Hồ Chí Minh  

(+84-28) 3855 8411  
(+84-28) 3853 7949  
(+84-28) 3855 5780  

Email: hanhchinh@ump.edu.vn
""")

# ================= FOOTER =================
st.markdown("---")
st.markdown("<center>© TS. Đào Hồng Nam</center>", unsafe_allow_html=True)
