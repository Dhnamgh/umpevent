import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import plotly.express as px

st.set_page_config(layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
html, body {
    font-family: Arial, sans-serif !important;
    font-size: 17px !important;
    color: #000 !important;
}
section[data-testid="stSidebar"] {
    width: 360px !important;
}
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

# ================= COLOR MAP =================
color_map = {
    dv: px.colors.qualitative.Plotly[i % 10]
    for i, dv in enumerate(df["donvi"].dropna().unique())
}

# ================= DASHBOARD CALENDAR =================
if menu == "Dashboard":

    st.subheader(f"📅 Lịch sự kiện - Tháng {today.month}/{today.year}")

    col1, col2, col3 = st.columns(3)

    if "view" not in st.session_state:
        st.session_state["view"] = "dayGridMonth"

    if col1.button("📅 Tháng"):
        st.session_state["view"] = "dayGridMonth"
    if col2.button("📆 Tuần"):
        st.session_state["view"] = "timeGridWeek"
    if col3.button("📊 Ngày"):
        st.session_state["view"] = "timeGridDay"

    view = st.session_state["view"]

    df_year = df_f[df_f["start"].dt.year == today.year]

    # ===== CALENDAR EVENT =====
    events = []

    for _, row in df_year.iterrows():
        events.append({
            "title": f"{row['event']} ({row['location']})",
            "start": row["start"].strftime("%Y-%m-%d %H:%M"),
            "end": row["end"].strftime("%Y-%m-%d %H:%M"),
            "color": color_map.get(row["donvi"], "#1976d2"),
        })

    calendar_options = {
        "initialView": view,
        "locale": "vi",
        "height": 650,
        "eventClick": "function(info) {alert(info.event.title);}",
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay"
        }
    }

    st.subheader("📆 Lịch trực quan")

    calendar(events=events, options=calendar_options)

    # ===== KPI =====
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    df_week = df_year[
        (df_year["start"] >= week_start) &
        (df_year["start"] <= week_end)
    ]

    df_month = df_year[df_year["start"].dt.month == today.month]

    c1, c2, c3 = st.columns(3)
    c1.metric("Tuần", len(df_week))
    c2.metric("Tháng", len(df_month))
    c3.metric("Năm", len(df_year))

    # ===== SUPPORT =====
    st.subheader("🛠️ Cần hỗ trợ (tháng hiện hành)")

    support_df = df_month[df_month["donvi"] == "Phòng Hành chính Tổng hợp"]

    if len(support_df) > 0:
        summary = support_df["support"].value_counts().reset_index()
        summary.columns = ["Loại hỗ trợ", "Số lượng"]

        st.table(summary)
    else:
        st.info("Không có yêu cầu hỗ trợ")

# ================= BÁO CÁO =================
elif menu == "Báo cáo":

    mode = st.radio("Chế độ", ["Tuần", "Tháng", "Năm"], horizontal=True)

    df_year = df_f[df_f["start"].dt.year == today.year]

    df_week = df_year[
        (df_year["start"] >= today - timedelta(days=7)) &
        (df_year["start"] <= today)
    ]

    df_month = df_year[df_year["start"].dt.month == today.month]

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

    st.subheader("⚠️ Trùng lịch (tháng + tháng kế)")

    df_check = df[
        (df["start"] >= today) &
        (df["start"] <= today + timedelta(days=30))
    ]

    for i in range(len(df_check)):
        for j in range(i+1, len(df_check)):
            if df_check.iloc[i]["start"] == df_check.iloc[j]["start"]:

                t = df_check.iloc[i]["start"].strftime("%H:%M %d/%m/%Y")

                st.warning(f"""
Trùng lịch: {t}
• {df_check.iloc[i]['event']} - {df_check.iloc[i]['location']}
• {df_check.iloc[j]['event']} - {df_check.iloc[j]['location']}
""")

# ================= TRỢ GIÚP =================
elif menu == "Trợ giúp":

    st.subheader("🤖 Trợ giúp")
    q = st.text_input("Nhập câu hỏi:")

    if q:
        q = q.lower()

        if "tuần" in q:
            res = df[(df["start"] >= today - timedelta(days=7))]
            st.dataframe(res)

        elif "tháng" in q:
            res = df[df["start"].dt.month == today.month]
            st.dataframe(res)

        elif "năm" in q:
            st.dataframe(df[df["start"].dt.year == today.year])

        elif "hỗ trợ" in q:
            res = df[df["donvi"] == "Phòng Hành chính Tổng hợp"]
            st.dataframe(res)

        else:
            st.info("Chưa hiểu câu hỏi")

# ================= PHÊ DUYỆT =================
elif menu == "Phê duyệt":

    st.subheader("📋 Sự kiện cần DUYỆT")

    df_month = df[df["start"].dt.month == today.month]

    st.dataframe(df_month.sort_values("start"))

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
