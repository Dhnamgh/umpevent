import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
from openai import OpenAI

st.set_page_config(layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
html, body {font-size:16px; color:#000;}
section[data-testid="stSidebar"] {width:360px !important;}
</style>
""", unsafe_allow_html=True)

# ================= LOAD DATA =================
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

# ================= GOOGLE SHEETS =================
def connect_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds)

def update_status(event, status):
    client = connect_sheet()
    sheet = client.open_by_url(st.secrets["data"]["sheet_url"]).sheet1
    data = sheet.get_all_records()

    for i, row in enumerate(data):
        if row["Tên sự kiện"] == event:
            sheet.update_cell(i+2, len(row)+1, status)
            return True
    return False

# ================= AI =================
def ask_ai(q):
    client = OpenAI(api_key=st.secrets["ai"]["api_key"])
    sample = df.head(50).to_string()

    prompt = f"""
Dữ liệu:
{sample}

Câu hỏi: {q}

Trả lời ngắn gọn.
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )

    return res.choices[0].message.content

# ================= MENU =================
menu = st.sidebar.radio("MENU",
    ["Dashboard", "Tổng hợp", "Trợ giúp", "Phê duyệt SK", "Liên hệ"]
)

# ================= FILTER =================
donvi_list = sorted(df["donvi"].dropna().unique())

selected = st.sidebar.multiselect(
    "Chọn đơn vị",
    ["Toàn trường"] + donvi_list,
    default=["Phòng Hành chính Tổng hợp"]
)

if "Toàn trường" in selected or len(selected)==0:
    df_f = df.copy()
else:
    df_f = df[df["donvi"].isin(selected)]

# ================= DASHBOARD =================
if menu=="Dashboard":

    df_year = df[df["start"].dt.year==today.year]
    df_month = df_year[df_year["start"].dt.month==today.month]
    df_week = df_year[df_year["start"]>=today-timedelta(days=7)]

    c1,c2,c3 = st.columns(3)
    c1.metric("Tuần", len(df_week))
    c2.metric("Tháng", len(df_month))
    c3.metric("Năm", len(df_year))

    st.subheader("Sự kiện tháng")
    st.dataframe(df_month.sort_values("start"))

    st.subheader("Timeline")
    fig=px.timeline(df_year, x_start="start", x_end="end", y="event", color="donvi")
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

# ================= AI =================
elif menu=="Trợ giúp":
    q = st.text_input("Hỏi")
    if q:
        st.write(ask_ai(q))

# ================= APPROVAL =================
elif menu=="Phê duyệt SK":

    pwd = st.text_input("Mật khẩu", type="password")

    if pwd==st.secrets["auth"]["password"]:

        event = st.selectbox("Sự kiện", df["event"])
        status = st.selectbox("Trạng thái",
            ["Thống nhất", "Chưa thống nhất", "Cần liên hệ"]
        )

        if st.button("Cập nhật"):
            if update_status(event, status):
                st.success("Đã lưu")
            else:
                st.error("Không tìm thấy")

    else:
        st.warning("Nhập mật khẩu")

# ================= CONTACT =================
elif menu=="Liên hệ":
    st.markdown("""
**Phòng Hành chính Tổng hợp**

217 Hồng Bàng, TP.HCM  
Email: hanhchinh@ump.edu.vn
""")

st.markdown("---")
st.markdown("<center>© TS. Đào Hồng Nam</center>", unsafe_allow_html=True)
