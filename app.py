import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import plotly.express as px
import re

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

# ================= PARSE TIME UMP =================
def parse_time(text):
    if pd.isna(text):
        return None
    text = str(text).lower()

    m = re.search(r"(\d{1,2})\s*[gh:]\s*(\d{0,2})", text)

    if m:
        hour = int(m.group(1))
        minute = m.group(2)
        minute = int(minute) if minute != "" else 0
        return hour, minute
    return None

# ================= LOAD =================
@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv(st.secrets["data"]["csv_url"])

    df.columns = df.columns.str.strip()

    df = df.rename(columns={
        "Tên sự kiện": "event",
        "Đơn vị phụ trách/ tổ chức": "donvi",
        "Ngày tổ chức": "start",
        "Ngày kết thúc": "end",
        "Địa điểm tổ chức": "location",
        "Số lượng": "people",
        "Hỗ trợ": "support",
        "Giờ bắt đầu": "start_time",
        "Giờ kết thúc": "end_time"
    })

    df["start"] = pd.to_datetime(df["start"], errors="coerce")
    df["end"] = pd.to_datetime(df["end"], errors="coerce")
    df["end"] = df["end"].fillna(df["start"])

    # ✅ GHÉP GIỜ
    if "start_time" in df.columns:
        for i in range(len(df)):
            t = parse_time(df.loc[i, "start_time"])
            if t:
                df.loc[i, "start"] = df.loc[i, "start"].replace(hour=t[0], minute=t[1])

    if "end_time" in df.columns:
        for i in range(len(df)):
            t = parse_time(df.loc[i, "end_time"])
            if t:
                df.loc[i, "end"] = df.loc[i, "end"].replace(hour=t[0], minute=t[1])

    return df

df = load_data()
today = datetime.today()

# ================= TITLE =================
st.title("📊 Quản lý sự kiện UMP")

# ================= FILTER =================
donvi_list = sorted(df["donvi"].dropna().unique())

selected = st.sidebar.multiselect(
    "Chọn đơn vị",
    ["Toàn trường"] + donvi_list,
    default=["Toàn trường"]
)

st.sidebar.write("✅ Đang chọn:", ", ".join(selected))

df_f = df if "Toàn trường" in selected else df[df["donvi"].isin(selected)]

# ================= COLOR =================
color_map = {
    dv: px.colors.qualitative.Plotly[i % 10]
    for i, dv in enumerate(df["donvi"].dropna().unique())
}

# ================= DASHBOARD =================
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

# ================= CALENDAR =================
events = []

for _, row in df_year.iterrows():

    start = row["start"]
    end = row["end"]

    has_time = not (start.hour == 0 and start.minute == 0)

    start_str = start.strftime("%Y-%m-%d %H:%M") if has_time else start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d %H:%M") if has_time else end.strftime("%Y-%m-%d")

    events.append({
        "title": f"{row['event']} ({row['location']})",
        "start": start_str,
        "end": end_str,
        "color": color_map.get(row["donvi"], "#1976d2")
    })

calendar(events=events, options={
    "initialView": view,
    "locale": "vi",
    "height": 650,
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek,timeGridDay"
    }
})

# ================= KPI =================
week_start = today - timedelta(days=today.weekday())
week_end = week_start + timedelta(days=6)

df_week = df_year[(df_year["start"] >= week_start) & (df_year["start"] <= week_end)]
df_month = df_year[df_year["start"].dt.month == today.month]

c1, c2, c3 = st.columns(3)
c1.metric("Tuần", len(df_week))
c2.metric("Tháng", len(df_month))
c3.metric("Năm", len(df_year))

# ================= SUPPORT =================
st.subheader("🛠️ Cần hỗ trợ (tháng hiện hành)")

support_df = df_month[df_month["donvi"] == "Phòng Hành chính Tổng hợp"]

if len(support_df) > 0 and "support" in support_df.columns:

    valid = support_df["support"].dropna()

    if len(valid) > 0:
        summary = valid.astype(str).value_counts().reset_index()
        summary.columns = ["Loại hỗ trợ", "Số lượng"]
        st.table(summary)
    else:
        st.info("Không có dữ liệu hỗ trợ")
else:
    st.info("Không có dữ liệu hỗ trợ")

# ================= WARNING =================
st.subheader("⚠️ Trùng lịch (30 ngày tới)")

df_check = df[(df["start"] >= today) & (df["start"] <= today + timedelta(days=30))]

for i in range(len(df_check)):
    for j in range(i+1, len(df_check)):
        if df_check.iloc[i]["start"] == df_check.iloc[j]["start"]:

            t = df_check.iloc[i]["start"]

            time_str = (
                t.strftime("%H:%M %d/%m/%Y")
                if not (t.hour == 0 and t.minute == 0)
                else t.strftime("%d/%m/%Y")
            )

            st.warning(f"""
Trùng lịch: {time_str}
• {df_check.iloc[i]['event']} - {df_check.iloc[i]['location']}
• {df_check.iloc[j]['event']} - {df_check.iloc[j]['location']}
""")

# ================= CONTACT =================
st.subheader("📞 Liên hệ")

st.markdown("""
Phòng Hành chính Tổng hợp  
217 Hồng Bàng, Phường Chợ Lớn, Thành phố Hồ Chí Minh  

(+84-28) 3855 8411  
(+84-28) 3853 7949  
(+84-28) 3855 5780  

Email: hanhchinh@ump.edu.vn
""")

st.markdown("---")
st.markdown("<center>© TS. Đào Hồng Nam</center>", unsafe_allow_html=True)
