import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re

st.set_page_config(layout="wide")

# ===== FIX FONT & CALENDAR =====
st.markdown("""
<style>
html, body {
    font-family: Arial, sans-serif;
    font-size: 18px;
    color: #000000;
}

/* sidebar */
section[data-testid="stSidebar"] {
    width: 350px !important;
}

/* FIX KHÔNG CẮT CHỮ */
.fc-event-title {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
}

/* cho event tự cao lên */
.fc-daygrid-event {
    height: auto !important;
    max-height: none !important;
}

/* tăng spacing */
.fc-daygrid-event-harness {
    margin-bottom: 3px !important;
}

/* hiển thị nhiều dòng */
.fc-daygrid-day-frame {
    min-height: 120px !important;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Quản lý sự kiện UMP")

# ===== PARSE GIỜ =====
def parse_time(text):
    if pd.isna(text):
        return None
    text = str(text).lower()
    m = re.search(r"(\\d{1,2})\\s*[gh:]\\s*(\\d{0,2})", text)
    if m:
        h = int(m.group(1))
        mnt = int(m.group(2)) if m.group(2) else 0
        return h, mnt
    return None

# ===== LOAD DATA =====
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
        t = parse_time(df.loc[i].get("start_time"))
        if t:
            df.loc[i, "start"] = df.loc[i, "start"].replace(hour=t[0], minute=t[1])

    return df

df = load_data()
today = datetime.today()

# ===== MENU =====
menu = st.sidebar.radio(
    "MENU",
    ["Dashboard", "Báo cáo", "Cảnh báo", "Trợ giúp", "Phê duyệt", "Liên hệ"]
)

# ===== FILTER =====
donvi_list = sorted(df["donvi"].dropna().unique())

selected = st.sidebar.multiselect(
    "Chọn đơn vị",
    ["Toàn trường"] + donvi_list,
    default=["Toàn trường"]
)

st.sidebar.success("✅ Đang chọn: " + ", ".join(selected))

df_f = df if "Toàn trường" in selected else df[df["donvi"].isin(selected)]

df_year = df_f[df_f["start"].dt.year == today.year]
df_month = df_year[df_year["start"].dt.month == today.month]

# ================= DASHBOARD =================
if menu == "Dashboard":

    st.subheader(f"📅 Lịch toàn trường - Tháng {today.month}/{today.year}")

    events = []

    for _, r in df_year.iterrows():
        s = r["start"]

        has_time = not (s.hour == 0 and s.minute == 0)

        time_str = s.strftime("%H:%M") if has_time else ""
        title = f"{time_str} {r['event']} ({r['location']})".strip()

        start_str = s.strftime("%Y-%m-%d %H:%M") if has_time else s.strftime("%Y-%m-%d")

        events.append({
            "title": title,
            "start": start_str
        })

    selected_event = calendar(
        events=events,
        options={
            "initialView": "dayGridMonth",
            "locale": "vi",
            "height": 700
        }
    )

    if selected_event and "event" in selected_event:
        st.subheader("📋 Chi tiết sự kiện")
        st.write(selected_event["event"]["title"])

# ================= BÁO CÁO =================
elif menu == "Báo cáo":

    mode = st.radio("Chọn loại báo cáo", ["Tuần", "Tháng", "Năm"])

    if mode == "Tuần":
        df_use = df_year[df_year["start"] >= today - timedelta(days=7)]
    elif mode == "Tháng":
        df_use = df_month
    else:
        df_use = df_year

    st.subheader(f"📊 Báo cáo {mode.lower()}")

    summary = df_use.groupby("donvi").size().reset_index(name="count")
    st.bar_chart(summary.set_index("donvi"))

# ================= CẢNH BÁO =================
elif menu == "Cảnh báo":

    df_check = df[
        (df["start"] >= today) &
        (df["start"] <= today + timedelta(days=30))
    ]

    for i in range(len(df_check)):
        for j in range(i+1, len(df_check)):
            if df_check.iloc[i]["start"] == df_check.iloc[j]["start"]:

                t = df_check.iloc[i]["start"]

                if t.hour == 0:
                    time_str = t.strftime("%d/%m/%Y")
                else:
                    time_str = t.strftime("%H:%M %d/%m/%Y")

                st.warning(f"""
Trùng lịch: {time_str}
• {df_check.iloc[i]['event']} - {df_check.iloc[i]['location']}
• {df_check.iloc[j]['event']} - {df_check.iloc[j]['location']}
""")

# ================= TRỢ GIÚP =================
elif menu == "Trợ giúp":

    q = st.text_input("Nhập câu hỏi")

    if q:
        if "tháng" in q:
            st.dataframe(df_month)
        elif "năm" in q:
            st.dataframe(df_year)

# ================= PHÊ DUYỆT =================
elif menu == "Phê duyệt":
    st.dataframe(df_month)

# ================= LIÊN HỆ =================
elif menu == "Liên hệ":
    st.markdown("""
Phòng Hành chính Tổng hợp  
217 Hồng Bàng, Phường Chợ Lớn, TP.HCM  

(+84-28) 3855 8411  
(+84-28) 3853 7949  
(+84-28) 3855 5780  

Email: hanhchinh@ump.edu.vn
""")

st.markdown("---")
st.markdown("© TS. Đào Hồng Nam")
