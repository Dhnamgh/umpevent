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
html, body {font-family: Arial; font-size:16px;}
section[data-testid="stSidebar"] {width:340px !important;}
</style>
""", unsafe_allow_html=True)

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

# ================= LOAD DATA =================
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
            df.loc[i,"start"] = df.loc[i,"start"].replace(hour=t[0], minute=t[1])

        t2 = parse_time(df.loc[i].get("end_time"))
        if t2:
            df.loc[i,"end"] = df.loc[i,"end"].replace(hour=t2[0], minute=t2[1])

    return df

df = load_data()
today = datetime.today()

# ================= MENU =================
menu = st.sidebar.radio(
    "MENU",
    ["Dashboard","Báo cáo","Cảnh báo","Trợ giúp","Phê duyệt","Liên hệ"]
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
df_month = df_year[df_year["start"].dt.month == today.month]

# ================= DASHBOARD =================
if menu == "Dashboard":

    st.subheader(f"📅 Lịch sự kiện - Tháng {today.month}/{today.year}")

    events = []

    for _, r in df_year.iterrows():
        s = r["start"]
        e = r["end"]

        has_time = not (s.hour == 0 and s.minute == 0)

        start_str = s.strftime("%Y-%m-%d %H:%M") if has_time else s.strftime("%Y-%m-%d")
        end_str = e.strftime("%Y-%m-%d %H:%M") if has_time else e.strftime("%Y-%m-%d")

        events.append({
            "title": r["event"],
            "start": start_str,
            "end": end_str,
            "extendedProps": {
                "event": r["event"],
                "donvi": r["donvi"],
                "location": r["location"],
                "time": start_str,
                "support": str(r.get("support",""))
            }
        })

    selected_event = calendar(
        events=events,
        options={
            "initialView":"dayGridMonth",
            "locale":"vi",
            "height":650
        }
    )

    # ✅ HIỂN THỊ CHI TIẾT (KHÔNG JS)
    if selected_event and "event" in selected_event:
        e = selected_event["event"]["extendedProps"]

        st.subheader("📋 Chi tiết sự kiện")

        st.write("📌", e.get("event",""))
        st.write("🏢", e.get("donvi",""))
        st.write("📍", e.get("location",""))
        st.write("🕒", e.get("time",""))
        st.write("🛠", e.get("support",""))

    # KPI
    df_week = df_year[
        (df_year["start"] >= today - timedelta(days=7))
    ]

    c1,c2,c3 = st.columns(3)
    c1.metric("Tuần", len(df_week))
    c2.metric("Tháng", len(df_month))
    c3.metric("Năm", len(df_year))

    # SUPPORT
    st.subheader("🛠️ Cần hỗ trợ")

    support_df = df_month[df_month["donvi"]=="Phòng Hành chính Tổng hợp"]

    if "support" in support_df.columns and len(support_df)>0:
        valid = support_df["support"].dropna()
        if len(valid)>0:
            ss = valid.value_counts().reset_index()
            ss.columns = ["Loại","Số lượng"]
            st.table(ss)
        else:
            st.info("Không có dữ liệu hỗ trợ")
    else:
        st.info("Không có dữ liệu hỗ trợ")

# ================= BÁO CÁO =================
elif menu=="Báo cáo":

    summary = df_month.groupby("donvi").size().reset_index(name="count")

    fig = px.bar(summary,x="donvi",y="count",text="count")
    fig.update_traces(textposition='outside')

    st.plotly_chart(fig,use_container_width=True)

# ================= CẢNH BÁO =================
elif menu=="Cảnh báo":

    st.subheader("⚠️ Trùng lịch")

    df_check = df[
        (df["start"]>=today) &
        (df["start"]<=today+timedelta(days=30))
    ]

    for i in range(len(df_check)):
        for j in range(i+1,len(df_check)):
            if df_check.iloc[i]["start"]==df_check.iloc[j]["start"]:

                t=df_check.iloc[i]["start"]

                time_str=(
                    t.strftime("%H:%M %d/%m/%Y")
                    if not (t.hour==0 and t.minute==0)
                    else t.strftime("%d/%m/%Y")
                )

                st.warning(f"""
Trùng lịch: {time_str}
• {df_check.iloc[i]['event']} - {df_check.iloc[i]['location']}
• {df_check.iloc[j]['event']} - {df_check.iloc[j]['location']}
""")

# ================= TRỢ GIÚP =================
elif menu=="Trợ giúp":

    st.subheader("Trợ giúp")
    q=st.text_input("Nhập câu hỏi")

    if q:
        q=q.lower()

        if "tháng" in q:
            st.dataframe(df_month)

        elif "năm" in q:
            st.dataframe(df_year)

        elif "tuần" in q:
            st.dataframe(df_year.tail(10))

        elif "hỗ trợ" in q:
            st.dataframe(df_month[df_month["donvi"]=="Phòng Hành chính Tổng hợp"])

# ================= PHÊ DUYỆT =================
elif menu=="Phê duyệt":

    st.subheader("📋 Sự kiện cần phê duyệt")

    st.dataframe(df_month)

# ================= LIÊN HỆ =================
elif menu=="Liên hệ":

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
