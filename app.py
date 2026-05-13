import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import plotly.express as px
import plotly.graph_objects as go
import re
import hashlib

st.set_page_config(layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
html, body {font-family: Arial, sans-serif; font-size:16px; color:#111827;}
section[data-testid="stSidebar"] {width:340px !important;}
.block-container {padding-top: 1rem;}
</style>
""", unsafe_allow_html=True)

st.title("📊 Quản lý sự kiện UMP")

# ================= HELPERS =================
def parse_time(text):
    if pd.isna(text):
        return None
    text = str(text).strip().lower()
    if not text or text in ["nan", "none"]:
        return None

    # 7g30, 07g, 7h, 13h00, 14:00
    m = re.search(r"(\d{1,2})\s*[gh:]\s*(\d{0,2})", text)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute

    # 7, 07, 13
    m = re.fullmatch(r"\d{1,2}", text)
    if m:
        hour = int(text)
        if 0 <= hour <= 23:
            return hour, 0

    return None


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def is_yes(value):
    txt = clean_text(value).upper()
    return txt in ["CÓ", "CO", "YES", "Y", "TRUE", "1"]


def count_value(value):
    """Convert support quantity to number. Text/CÓ = 1, empty/KHÔNG/0 = 0."""
    txt = clean_text(value)
    if not txt:
        return 0
    up = txt.upper()
    if up in ["KHÔNG", "KHONG", "NO", "N", "FALSE"]:
        return 0

    m = re.search(r"\d+", txt.replace(",", "."))
    if m:
        try:
            return int(m.group(0))
        except Exception:
            return 0

    if up in ["CÓ", "CO", "YES", "Y", "TRUE"]:
        return 1

    return 1


def event_color(index, key):
    """Create stable, highly varied colors by event, not by unit."""
    palette = [
        "#00695C", "#C62828", "#1565C0", "#EF6C00", "#6A1B9A",
        "#2E7D32", "#AD1457", "#283593", "#00838F", "#5D4037",
        "#9E2A2B", "#3F51B5", "#00796B", "#F57C00", "#7B1FA2",
        "#455A64", "#D84315", "#1B5E20", "#4E342E", "#0277BD"
    ]
    digest = int(hashlib.md5(str(key).encode("utf-8")).hexdigest(), 16)
    return palette[(digest + index) % len(palette)]


def wrap_label(text, width=24):
    words = str(text).split()
    lines = []
    line = ""
    for w in words:
        if len(line + " " + w) <= width:
            line = (line + " " + w).strip()
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return "<br>".join(lines)


def get_period_df(df_input, period):
    now = datetime.today()
    if period == "Tuần":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        label = f"Tuần {start.strftime('%d/%m/%Y')} - {(end - timedelta(days=1)).strftime('%d/%m/%Y')}"
    elif period == "Tháng":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        label = f"Tháng {now.month}/{now.year}"
    else:
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year + 1)
        label = f"Năm {now.year}"

    out = df_input[(df_input["start"] >= start) & (df_input["start"] < end)]
    return out, label, start, end


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
        "Một số ĐỀ XUẤT HỖ TRỢ từ phòng Hành chính Tổng hợp": "support",
        "Giờ bắt đầu": "start_time",
        "Giờ kết thúc": "end_time",
        "Số lượng bàn đón tiếp": "support_ban_don_tiep",
        "Cần trải khăn bàn hội trường": "support_khan_ban",
        "Số lượng lễ tân": "support_le_tan",
        "Số lượng bảng tên (bảng mica)": "support_bang_ten",
        "Số lượng bìa ký kết": "support_bia_ky_ket",
        "Số lượng nước uống": "support_nuoc_uong",
        "Số phần Teabreak": "support_teabreak",
        "Số lượng hoa để bàn": "support_hoa_ban",
        "Số lượng hoa để bục phát biểu": "support_hoa_buc",
        "Số lượng hoa bó để tặng": "support_hoa_tang",
        "Số lượng quà tặng": "support_qua_tang",
        "Số lượng Brochure": "support_brochure",
        "Số lượng khay bưng": "support_khay_bung",
        "Số lượng bandroll, standee cần in và thi công": "support_bandroll_standee",
        "Số lượng Backdrop cần in và thi công": "support_backdrop",
        "Cần chạy bảng điện tử": "support_bang_dien_tu",
        "Cần gửi thư mời": "support_thu_moi",
        "Các yêu cầu khác (nếu có)": "support_khac"
    })

    df["start"] = pd.to_datetime(df["start"], errors="coerce")
    df["end"] = pd.to_datetime(df["end"], errors="coerce")
    df["end"] = df["end"].fillna(df["start"])

    df = df.dropna(subset=["start"])

    for i in df.index:
        t = parse_time(df.at[i, "start_time"] if "start_time" in df.columns else None)
        if t and pd.notna(df.at[i, "start"]):
            df.at[i, "start"] = df.at[i, "start"].replace(hour=t[0], minute=t[1])

        t2 = parse_time(df.at[i, "end_time"] if "end_time" in df.columns else None)
        if t2 and pd.notna(df.at[i, "end"]):
            df.at[i, "end"] = df.at[i, "end"].replace(hour=t2[0], minute=t2[1])

    for col in ["event", "donvi", "location", "support"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].apply(clean_text)

    return df


def build_support_table(df_input):
    support_cols = {
        "support_ban_don_tiep": "Bàn đón tiếp",
        "support_khan_ban": "Trải khăn bàn hội trường",
        "support_le_tan": "Lễ tân",
        "support_bang_ten": "Bảng tên/bảng mica",
        "support_bia_ky_ket": "Bìa ký kết",
        "support_nuoc_uong": "Nước uống",
        "support_teabreak": "Teabreak",
        "support_hoa_ban": "Hoa để bàn",
        "support_hoa_buc": "Hoa bục phát biểu",
        "support_hoa_tang": "Hoa bó tặng",
        "support_qua_tang": "Quà tặng",
        "support_brochure": "Brochure",
        "support_khay_bung": "Khay bưng",
        "support_bandroll_standee": "Bandroll/standee",
        "support_backdrop": "Backdrop",
        "support_bang_dien_tu": "Bảng điện tử",
        "support_thu_moi": "Gửi thư mời",
        "support_khac": "Yêu cầu khác"
    }

    rows = []
    for _, r in df_input.iterrows():
        has_support_flag = is_yes(r.get("support", ""))
        for col, label in support_cols.items():
            if col not in df_input.columns:
                continue
            raw = r.get(col, "")
            qty = count_value(raw)
            if qty > 0:
                rows.append({
                    "Sự kiện": r.get("event", ""),
                    "Ngày": r.get("start").strftime("%d/%m/%Y %H:%M") if pd.notna(r.get("start")) else "",
                    "Đơn vị": r.get("donvi", ""),
                    "Địa điểm": r.get("location", ""),
                    "Hỗ trợ": label,
                    "Số lượng": qty,
                    "Ghi chú/Giá trị gốc": clean_text(raw)
                })

        # Nếu đánh dấu CÓ nhưng không nhập chi tiết số lượng
        if has_support_flag and not any(count_value(r.get(c, "")) > 0 for c in support_cols):
            rows.append({
                "Sự kiện": r.get("event", ""),
                "Ngày": r.get("start").strftime("%d/%m/%Y %H:%M") if pd.notna(r.get("start")) else "",
                "Đơn vị": r.get("donvi", ""),
                "Địa điểm": r.get("location", ""),
                "Hỗ trợ": "Có yêu cầu hỗ trợ",
                "Số lượng": 1,
                "Ghi chú/Giá trị gốc": clean_text(r.get("support", ""))
            })

    return pd.DataFrame(rows)


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
    ["Toàn trường"] + list(donvi_list),
    default=["Toàn trường"]
)
st.sidebar.write("✅ Đang chọn:", ", ".join(selected))

df_f = df if "Toàn trường" in selected else df[df["donvi"].isin(selected)]
df_year = df_f[df_f["start"].dt.year == today.year]
df_month = df_year[df_year["start"].dt.month == today.month]

# ================= DASHBOARD =================
if menu == "Dashboard":
    st.subheader(f"📅 Lịch toàn trường - Tháng {today.month}/{today.year}")

    events = []
    for idx, (_, r) in enumerate(df_year.iterrows()):
        s = r["start"]
        e = r["end"]
        has_time = not (s.hour == 0 and s.minute == 0)

        start_str = s.strftime("%Y-%m-%d %H:%M") if has_time else s.strftime("%Y-%m-%d")
        end_str = e.strftime("%Y-%m-%d %H:%M") if has_time else e.strftime("%Y-%m-%d")

        time_label = s.strftime("%H:%M") if has_time else "Cả ngày"
        location = clean_text(r.get("location", ""))
        title = f"{time_label} - {r['event']}"
        if location:
            title += f"\n📍 {location}"

        color = event_color(idx, f"{r.get('event','')}-{s}-{location}")

        events.append({
            "title": title,
            "start": start_str,
            "end": end_str,
            "backgroundColor": color,
            "borderColor": color,
            "textColor": "#FFFFFF",
            "extendedProps": {
                "event": r.get("event", ""),
                "donvi": r.get("donvi", ""),
                "location": location,
                "time": start_str,
                "support": clean_text(r.get("support", ""))
            }
        })

    selected_event = calendar(
        events=events,
        options={
            "initialView": "dayGridMonth",
            "locale": "vi",
            "height": "auto",
            "contentHeight": "auto",
            "expandRows": False,
            "eventDisplay": "block",
            "displayEventTime": False,
            "dayMaxEventRows": False,
            "eventMaxStack": 50,
            "fixedWeekCount": False,
            "handleWindowResize": True
        },
        custom_css="""
        .fc { font-family: Arial, sans-serif !important; color:#111827 !important; }
        .fc-toolbar-title { font-size: 28px !important; font-weight: 800 !important; color:#111827 !important; }
        .fc-col-header-cell-cushion, .fc-daygrid-day-number { color:#111827 !important; font-weight:700 !important; }
        .fc-daygrid-day-frame { min-height: 170px !important; height: auto !important; padding: 2px !important; }
        .fc-daygrid-day-events { min-height: 1px !important; margin-bottom: 4px !important; }
        .fc-daygrid-event-harness { position: relative !important; margin-top: 4px !important; }
        .fc-daygrid-event { white-space: normal !important; overflow: visible !important; padding: 4px 5px !important; border-radius: 6px !important; }
        .fc-event-main { white-space: normal !important; overflow: visible !important; }
        .fc-event-title-container { white-space: normal !important; overflow: visible !important; }
        .fc-event-title { white-space: pre-line !important; overflow: visible !important; text-overflow: unset !important; line-height: 1.35 !important; font-size: 12.5px !important; font-weight: 700 !important; }
        .fc-daygrid-block-event .fc-event-title { white-space: pre-line !important; }
        """
    )

    if selected_event and "event" in selected_event:
        e = selected_event["event"]["extendedProps"]
        st.subheader("📋 Chi tiết sự kiện")
        st.write("📌", e.get("event", ""))
        st.write("🏢", e.get("donvi", ""))
        st.write("📍", e.get("location", ""))
        st.write("🕒", e.get("time", ""))
        st.write("🛠", e.get("support", ""))

    st.subheader("📈 Tổng quan")
    start_week = today - timedelta(days=today.weekday())
    start_week = start_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_week = start_week + timedelta(days=7)
    df_week = df_year[(df_year["start"] >= start_week) & (df_year["start"] < end_week)]

    c1, c2, c3 = st.columns(3)
    c1.metric("Tuần", len(df_week))
    c2.metric("Tháng", len(df_month))
    c3.metric("Năm", len(df_year))

    st.subheader("🛠️ Cần hỗ trợ")
    support_table = build_support_table(df_month)
    if len(support_table) == 0:
        st.info("Không có thông tin cần hỗ trợ")
    else:
        support_sum = support_table.groupby("Hỗ trợ", as_index=False)["Số lượng"].sum().sort_values("Số lượng", ascending=False)
        st.dataframe(support_sum, use_container_width=True)

# ================= BÁO CÁO =================
elif menu == "Báo cáo":
    st.subheader("📊 Báo cáo sự kiện theo đơn vị")

    report_period = st.radio(
        "Chọn kỳ báo cáo",
        ["Tuần", "Tháng", "Năm"],
        horizontal=True,
        index=1
    )

    df_report, report_label, _, _ = get_period_df(df_f, report_period)
    st.markdown(f"### Báo cáo: {report_label}")

    if len(df_report) == 0:
        st.info(f"Không có sự kiện trong {report_label.lower()}")
    else:
        summary = (
            df_report.groupby("donvi")
            .size()
            .reset_index(name="Số sự kiện")
            .sort_values("Số sự kiện", ascending=True)
        )
        summary["Đơn vị hiển thị"] = summary["donvi"].apply(lambda x: wrap_label(x, 36))

        fig = px.bar(
            summary,
            x="Số sự kiện",
            y="Đơn vị hiển thị",
            text="Số sự kiện",
            color="donvi",
            orientation="h",
            height=max(520, 48 * len(summary) + 180),
            hover_data={"donvi": True, "Đơn vị hiển thị": False}
        )

        fig.update_traces(
            textposition="outside",
            textfont=dict(size=16, color="black", family="Arial Black")
        )

        fig.update_layout(
            title=dict(text=f"Số sự kiện theo đơn vị - {report_label}", font=dict(size=22, color="black", family="Arial Black")),
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=40, r=90, t=70, b=40),
            xaxis=dict(title="Số sự kiện", tickfont=dict(size=15, color="black", family="Arial"), title_font=dict(size=16, color="black", family="Arial Black")),
            yaxis=dict(title="", tickfont=dict(size=15, color="black", family="Arial Black"), automargin=True)
        )

        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(summary[["donvi", "Số sự kiện"]].sort_values("Số sự kiện", ascending=False), use_container_width=True)

# ================= CẢNH BÁO =================
elif menu == "Cảnh báo":
    st.subheader("⚠️ Trùng lịch")

    df_check = df_f[(df_f["start"] >= today) & (df_f["start"] <= today + timedelta(days=30))].copy()
    found = False

    for i in range(len(df_check)):
        for j in range(i + 1, len(df_check)):
            s1 = df_check.iloc[i]["start"]
            s2 = df_check.iloc[j]["start"]
            loc1 = clean_text(df_check.iloc[i].get("location", ""))
            loc2 = clean_text(df_check.iloc[j].get("location", ""))

            same_time = s1 == s2
            overlap = df_check.iloc[i]["start"] < df_check.iloc[j]["end"] and df_check.iloc[j]["start"] < df_check.iloc[i]["end"]

            if same_time or overlap:
                found = True
                time_str_1 = s1.strftime("%H:%M %d/%m/%Y") if not (s1.hour == 0 and s1.minute == 0) else s1.strftime("%d/%m/%Y")
                time_str_2 = s2.strftime("%H:%M %d/%m/%Y") if not (s2.hour == 0 and s2.minute == 0) else s2.strftime("%d/%m/%Y")

                st.warning(f"""
🕒 Thời gian trùng/chồng lấn:

• {time_str_1} - {df_check.iloc[i]['event']}
  - Địa điểm: {loc1}

• {time_str_2} - {df_check.iloc[j]['event']}
  - Địa điểm: {loc2}
""")

    if not found:
        st.success("Không phát hiện lịch bị trùng trong 30 ngày tới")

# ================= TRỢ GIÚP =================
elif menu == "Trợ giúp":
    st.subheader("🤖 Trợ giúp")
    q = st.text_input("Nhập câu hỏi, ví dụ: tuần, tháng, năm, hỗ trợ")

    if q:
        q = q.lower()

        if "tuần" in q:
            week_df, label, _, _ = get_period_df(df_f, "Tuần")
            st.write(f"📅 Sự kiện {label}")
            if len(week_df) > 0:
                st.dataframe(week_df, use_container_width=True)
            else:
                st.info("Không có sự kiện trong tuần này")

        elif "tháng" in q:
            month_df, label, _, _ = get_period_df(df_f, "Tháng")
            st.write(f"📅 Sự kiện {label}")
            if len(month_df) > 0:
                st.dataframe(month_df, use_container_width=True)
            else:
                st.info("Không có sự kiện trong tháng")

        elif "năm" in q:
            year_df, label, _, _ = get_period_df(df_f, "Năm")
            st.write(f"📅 Sự kiện {label}")
            if len(year_df) > 0:
                st.dataframe(year_df, use_container_width=True)
            else:
                st.info("Không có sự kiện trong năm")

        elif "hỗ trợ" in q or "ho tro" in q:
            support_df = build_support_table(df_f)

            if len(support_df) == 0:
                st.info("Không có thông tin cần hỗ trợ")
            else:
                st.write("### Danh sách sự kiện cần hỗ trợ")
                st.dataframe(support_df, use_container_width=True)

                chart_df = (
                    support_df.groupby(["Sự kiện", "Hỗ trợ"], as_index=False)["Số lượng"]
                    .sum()
                    .sort_values("Số lượng", ascending=False)
                )

                fig = px.bar(
                    chart_df,
                    x="Sự kiện",
                    y="Số lượng",
                    color="Hỗ trợ",
                    text="Số lượng",
                    barmode="group",
                    height=max(560, 80 + 45 * chart_df["Sự kiện"].nunique())
                )

                fig.update_traces(textposition="outside", textfont=dict(size=14, color="black", family="Arial Black"))
                fig.update_layout(
                    title=dict(text="Thống kê sự kiện cần hỗ trợ", font=dict(size=22, color="black", family="Arial Black")),
                    xaxis=dict(title="Sự kiện", tickangle=-25, tickfont=dict(size=13, color="black", family="Arial Black"), automargin=True),
                    yaxis=dict(title="Số lượng", tickfont=dict(size=14, color="black")),
                    legend=dict(title="Loại hỗ trợ", font=dict(size=13, color="black")),
                    plot_bgcolor="white",
                    margin=dict(l=40, r=40, t=70, b=140)
                )

                st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning("Không hiểu yêu cầu. Hãy nhập: tuần, tháng, năm hoặc hỗ trợ")

# ================= PHÊ DUYỆT =================
elif menu == "Phê duyệt":
    st.subheader("📋 Sự kiện cần phê duyệt")
    st.dataframe(df_month, use_container_width=True)

# ================= LIÊN HỆ =================
elif menu == "Liên hệ":
    st.markdown("""
### Phòng Hành chính Tổng hợp

217 Hồng Bàng, Phường Chợ Lớn, TP.HCM

☎ (+84-28) 3855 8411  
☎ (+84-28) 3853 7949  
☎ (+84-28) 3855 5780

📧 hanhchinh@ump.edu.vn
""")

st.markdown("---")
st.markdown("© TS. Đào Hồng Nam")
