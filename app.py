import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import plotly.express as px
import re

st.set_page_config(layout="wide")

# ================= STYLE FIX =================
st.markdown("""
<style>

/* sidebar rộng */
section[data-testid="stSidebar"] {
    width: 340px !important;
}

/* FIX FULLCALENDAR TEXT */
.fc-event-title {
    white-space: normal !important;
    overflow: visible !important;
}

.fc-daygrid-event {
    height: auto !important;
}

.fc-event {
    font-size: 12px !important;
}

/* tooltip đẹp hơn */
.fc-event:hover {
    z-index: 999 !important;
}

</style>
""", unsafe_allow_html=True)

# ================= TITLE =================
st.title("📊 Quản lý sự kiện UMP")

# ================= PARSE GIỜ =================
def parse_time(text):
    if pd.isna(text):
        return None
    text = str(text).lower()

    m = re.search(r"(\\d{1,2})\\s*[gh:]\\s*(\\d{0,2})", text)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        return hour, minute
    return None

# ================= LOAD =================
@st.cache_data
def load_data():
    df = pd.read_csv(st.secrets["data"]["csv_url"])
    df.columns = df.columns.str.strip()

    df = df.rename(columns={
        "Tên sự kiện": "event",
        "Đơn vị phụ trách/ tổ chức": "donvi",
        "Ngày tổ chức": "start",
        "Ngày kết thúc": "end",
        "Địa điểm tổ chức": "location",
        "Hỗ trợ": "support",
        "Giờ bắt đầu": "start_time",
        "Giờ kết thúc": "end_time"
    })

    df["start"] = pd.to_datetime(df["start"], errors="coerce")
    df["end"] = pd.to_datetime(df["end"], errors="coerce").fillna(df["start"])

    for i in range(len(df)):
        t = parse_time(df.loc[i, "start_time"])
        if t:
            df.loc[i, "start"] = df.loc[i, "start"].replace(hour=t[0], minute=t[1])

        t2 = parse_time(df.loc[i, "end_time"])
        if t2:
            df.loc[i, "end"] = df.loc[i, "end"].replace(hour=t2[0], minute=t2[1])

    return df

df = load_data()
today = datetime.today()

# ================= MENU =================
menu = st.sidebar.radio(
    "MENU",
    ["Dashboard", "Cảnh báo", "Liên hệ"]
)

# ================= FILTER =================
donvi_list = sorted(df["donvi"].dropna().unique())

selected = st.sidebar.multiselect(
    "Chọn đơn vị",
    ["Toàn trường"] + donvi_list,
    default=["Toàn trường"]
)

st.sidebar.write("✅ Đang chọn:", ", ".join(selected))

df_f = df if "Toàn trường" in selected else df[df["donvi"].isin(selected)]

df_year = df_f[df_f["start"].dt.year == today.year]

# ================= DASHBOARD =================
if menu == "Dashboard":

    st.subheader(f"📅 Lịch sự kiện - Tháng {today.month}/{today.year}")

    # ===== BUILD EVENTS =====
    events = []

    for _, row in df_year.iterrows():

        s = row["start"]
        e = row["end"]

        has_time = not (s.hour == 0 and s.minute == 0)

        start_str = s.strftime("%Y-%m-%d %H:%M") if has_time else s.strftime("%Y-%m-%d")
        end_str = e.strftime("%Y-%m-%d %H:%M") if has_time else e.strftime("%Y-%m-%d")

        full_info = f"{row['event']} | {row['location']}"

        events.append({
            "title": row["event"],
            "start": start_str,
            "end": end_str,
            "color": "#1976d2",
            "extendedProps": {
                "info": full_info,
                "donvi": row["donvi"],
                "location": row["location"],
                "time": start_str,
                "support": str(row.get("support",""))
            }
        })

    # ===== CALENDAR =====
    options = {
        "initialView": "dayGridMonth",
        "locale": "vi",
        "height": 650,

        # ✅ TOOLTIP FULL
        "eventDidMount": """
function(info) {
    info.el.title = info.event.extendedProps.info;
}
""",

        # ✅ CLICK DETAIL
        "eventClick": """
function(info) {
    let e = info.event.extendedProps;

    alert(
        "Sự kiện: " + info.event.title + "\\n" +
        "Đơn vị: " + e.donvi + "\\n" +
        "Địa điểm: " + e.location + "\\n" +
        "Thời gian: " + e.time + "\\n" +
        "Hỗ trợ: " + e.support
    );
}
"""
    }

    calendar(events=events, options=options)

# ================= CẢNH BÁO =================
elif menu == "Cảnh báo":

    st.subheader("⚠️ Trùng lịch")

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

# ================= LIÊN HỆ =================
elif menu == "Liên hệ":

    st.markdown("""
### 📞 Phòng Hành chính Tổng hợp

217 Hồng Bàng, Phường Chợ Lớn, TP.HCM  

(+84-28) 3855 8411  
(+84-28) 3853 7949  
(+84-28) 3855 5780  

Email: hanhchinh@ump.edu.vn
""")
