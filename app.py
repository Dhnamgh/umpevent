import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import plotly.express as px
import re
import hashlib
from io import BytesIO

st.set_page_config(layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
html, body {font-family: Arial, sans-serif; font-size:16px; color:#111827;}
section[data-testid="stSidebar"] {width:255px !important; min-width:255px !important; max-width:255px !important;}
.block-container {padding-top: 1rem;}

.table-title {
    font-size: 22px;
    font-weight: 900;
    color: #020617;
    margin-top: 18px;
    margin-bottom: 10px;
    font-family: Arial, sans-serif;
    letter-spacing: -0.2px;
}

.small-note {
    color:#111827;
    font-weight:700;
}

.ump-table-wrap {
    width: 100%;
    overflow-x: auto;
    margin-bottom: 10px;
}

.ump-table-wrap.compact {
    width: fit-content;
    max-width: 100%;
}

.ump-table {
    border-collapse: collapse;
    font-family: Arial, sans-serif;
    font-size: 15px;
    color: #020617 !important;
    background: white;
}

.ump-table th {
    background: #f1f5f9;
    color: #020617 !important;
    font-weight: 900;
    border: 1px solid #cbd5e1;
    padding: 8px 10px;
    text-align: left;
    white-space: nowrap;
}

.ump-table td {
    color: #020617 !important;
    font-weight: 650;
    border: 1px solid #cbd5e1;
    padding: 7px 10px;
    vertical-align: top;
    line-height: 1.35;
}

.ump-table.compact th,
.ump-table.compact td {
    white-space: nowrap;
}

.ump-table tr:nth-child(even) td {
    background: #f8fafc;
}
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
    if up in ["KHÔNG", "KHONG", "NO", "N", "FALSE", "0"]:
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
    """Create stable colors by event, reducing repeated adjacent colors."""
    palette = [
        "#DBEAFE", "#DCFCE7", "#FEE2E2", "#FFEDD5", "#F3E8FF",
        "#CCFBF1", "#FCE7F3", "#E0E7FF", "#CFFAFE", "#FEF3C7",
        "#E5E7EB", "#D1FAE5", "#FAE8FF", "#EDE9FE", "#FDE68A",
        "#BFDBFE", "#BBF7D0", "#FECACA", "#FED7AA", "#DDD6FE"
    ]
    digest = int(hashlib.md5(str(key).encode("utf-8")).hexdigest(), 16)
    return palette[(digest + index) % len(palette)]


def wrap_label(text, width=28):
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

    out = df_input[(df_input["start"] >= start) & (df_input["start"] < end)].copy()
    return out, label, start, end


def dataframe_to_excel_bytes(dataframe):
    """
    Tạo file Excel dạng .xls bằng HTML để tránh lỗi thiếu module openpyxl/xlsxwriter
    trên Streamlit Cloud. Excel vẫn mở được bình thường.
    """
    html = dataframe.to_html(index=False, escape=False)
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            table {{ border-collapse: collapse; font-family: Arial, sans-serif; }}
            th {{ background: #e5e7eb; font-weight: bold; }}
            th, td {{ border: 1px solid #999; padding: 6px; }}
        </style>
    </head>
    <body>{html}</body>
    </html>
    """
    return html.encode("utf-8-sig")


def excel_file_name(file_name):
    base = str(file_name).rsplit(".", 1)[0]
    return base + ".xls"


def show_table_with_download(title, dataframe, file_name, compact=False):
    st.markdown(f'<div class="table-title">{title}</div>', unsafe_allow_html=True)

    if dataframe is None or len(dataframe) == 0:
        st.info("Không có dữ liệu")
        return

    css_class = "ump-table compact" if compact else "ump-table"
    wrap_class = "ump-table-wrap compact" if compact else "ump-table-wrap"
    html_table = dataframe.to_html(index=False, escape=False, classes=css_class)
    st.markdown(f'<div class="{wrap_class}">{html_table}</div>', unsafe_allow_html=True)

    st.download_button(
        label="⬇️ Tải về Excel",
        data=dataframe_to_excel_bytes(dataframe),
        file_name=excel_file_name(file_name),
        mime="application/vnd.ms-excel",
        use_container_width=False
    )


def collapse_repeated_support_rows(dataframe):
    """Ẩn thông tin lặp lại cho cùng một sự kiện để bảng hỗ trợ dễ đọc hơn."""
    if dataframe is None or len(dataframe) == 0:
        return dataframe

    df_out = dataframe.copy()
    group_cols = ["Sự kiện", "Đơn vị", "Ngày giờ", "Địa điểm"]
    existing = [c for c in group_cols if c in df_out.columns]
    if not existing:
        return df_out

    last_key = None
    for idx in df_out.index:
        key = tuple(df_out.at[idx, c] for c in existing)
        if key == last_key:
            for c in existing:
                df_out.at[idx, c] = ""
        else:
            last_key = key

    return df_out


def build_approval_summary_table(df_input):
    """Tạo bảng Phê duyệt gọn từ dữ liệu gốc giống bản v6, chỉ giữ các cột quan trọng."""
    columns = ["Sự kiện", "Đơn vị", "Ngày giờ", "Địa điểm", "Hỗ trợ"]

    if df_input is None or len(df_input) == 0:
        return pd.DataFrame(columns=columns)

    rows = []
    df_out = df_input.copy()
    df_out["_sort_time"] = pd.to_datetime(df_out["start"], errors="coerce")
    df_out = df_out.sort_values(["_sort_time", "donvi", "event"], ascending=[True, True, True]).reset_index(drop=True)

    for _, r in df_out.iterrows():
        s = r.get("start")
        if pd.notna(s):
            if s.hour == 0 and s.minute == 0:
                ngay_gio = s.strftime("%d/%m/%Y")
            else:
                ngay_gio = s.strftime("%d/%m/%Y %H:%M")
        else:
            ngay_gio = ""

        ho_tro = clean_text(r.get("support", ""))
        if not ho_tro:
            ho_tro = "Không"

        rows.append({
            "Sự kiện": clean_text(r.get("event", "")),
            "Đơn vị": clean_text(r.get("donvi", "")),
            "Ngày giờ": ngay_gio,
            "Địa điểm": clean_text(r.get("location", "")),
            "Hỗ trợ": ho_tro
        })

    return pd.DataFrame(rows, columns=columns)


def build_event_query_table(df_input):
    """Bảng rút gọn cho Truy vấn AI, chỉ giữ các cột quan trọng và sắp xếp theo thời gian."""
    columns = ["Sự kiện", "Đơn vị", "Ngày giờ", "Địa điểm", "Hỗ trợ"]

    if df_input is None or len(df_input) == 0:
        return pd.DataFrame(columns=columns)

    rows = []
    df_out = df_input.copy()
    df_out["_sort_time"] = pd.to_datetime(df_out["start"], errors="coerce")
    df_out = df_out.sort_values(["_sort_time", "donvi", "event"], ascending=[True, True, True]).reset_index(drop=True)

    for _, r in df_out.iterrows():
        s = r.get("start")
        if pd.notna(s):
            if s.hour == 0 and s.minute == 0:
                ngay_gio = s.strftime("%d/%m/%Y")
            else:
                ngay_gio = s.strftime("%d/%m/%Y %H:%M")
        else:
            ngay_gio = ""

        ho_tro = clean_text(r.get("support", ""))
        if not ho_tro:
            ho_tro = "Không"

        rows.append({
            "Sự kiện": clean_text(r.get("event", "")),
            "Đơn vị": clean_text(r.get("donvi", "")),
            "Ngày giờ": ngay_gio,
            "Địa điểm": clean_text(r.get("location", "")),
            "Hỗ trợ": ho_tro
        })

    return pd.DataFrame(rows, columns=columns)


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
        has_detail = False

        for col, label in support_cols.items():
            if col not in df_input.columns:
                continue

            raw = r.get(col, "")
            qty = count_value(raw)

            if qty > 0:
                has_detail = True
                rows.append({
                    "Sự kiện": r.get("event", ""),
                    "Đơn vị": r.get("donvi", ""),
                    "Ngày giờ": r.get("start").strftime("%d/%m/%Y %H:%M") if pd.notna(r.get("start")) else "",
                    "Địa điểm": r.get("location", ""),
                    "Nội dung hỗ trợ": label,
                    "Số lượng": qty,
                    "Ghi chú/Giá trị gốc": clean_text(raw)
                })

        # Nếu có đánh dấu hỗ trợ nhưng không có cột chi tiết số lượng
        if has_support_flag and not has_detail:
            rows.append({
                "Sự kiện": r.get("event", ""),
                "Đơn vị": r.get("donvi", ""),
                "Ngày giờ": r.get("start").strftime("%d/%m/%Y %H:%M") if pd.notna(r.get("start")) else "",
                "Địa điểm": r.get("location", ""),
                "Nội dung hỗ trợ": "Có yêu cầu hỗ trợ",
                "Số lượng": 1,
                "Ghi chú/Giá trị gốc": clean_text(r.get("support", ""))
            })

    return pd.DataFrame(rows)


# ================= DATA =================
df = load_data()
today = datetime.today()

# ================= MENU =================
menu = st.sidebar.radio(
    "MENU",
    ["Dashboard", "Báo cáo", "Cảnh báo", "Hỗ trợ", "Truy vấn AI", "Phê duyệt", "Liên hệ"]
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

    for idx, (_, r) in enumerate(df_year.sort_values("start").iterrows()):
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
            "textColor": "#111827",
            "extendedProps": {
                "event": r.get("event", ""),
                "donvi": r.get("donvi", ""),
                "location": location,
                "time": start_str,
                "support": clean_text(r.get("support", ""))
            }
        })

    st.markdown("""
    <style>
    .calendar-mobile-scroll {
        width: 100%;
        overflow-x: auto;
        overflow-y: hidden;
        -webkit-overflow-scrolling: touch;
        touch-action: pan-x;
    }

    .calendar-mobile-inner {
        min-width: 1200px;
    }

    @media (max-width: 768px) {
        .calendar-mobile-scroll {
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding-bottom: 6px;
        }

        .calendar-mobile-inner,
        .calendar-mobile-inner .fc,
        .calendar-mobile-inner .fc-view-harness,
        .calendar-mobile-inner .fc-scrollgrid,
        .calendar-mobile-inner table {
            min-width: 1400px !important;
            width: 1400px !important;
        }

        .calendar-mobile-inner .fc-daygrid-day {
            min-width: 190px !important;
        }

        .calendar-mobile-inner .fc-daygrid-day-frame {
            min-height: 135px !important;
        }

        .calendar-mobile-inner .fc-daygrid-week:has(.fc-daygrid-event) .fc-daygrid-day-frame,
        .calendar-mobile-inner .fc-scrollgrid-sync-table tr:has(.fc-daygrid-event) .fc-daygrid-day-frame {
            min-height: 190px !important;
        }

        .calendar-mobile-inner .fc-event-title {
            font-size: 12px !important;
            line-height: 1.28 !important;
        }

        .calendar-mobile-inner .fc-toolbar {
            flex-wrap: nowrap !important;
            gap: 8px !important;
        }

        .calendar-mobile-inner .fc-toolbar-title {
            font-size: 22px !important;
            white-space: nowrap !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="calendar-mobile-scroll"><div class="calendar-mobile-inner">',
        unsafe_allow_html=True
    )

    selected_event = calendar(
        events=events,
        options={
            "initialView": "dayGridMonth",
            "locale": "vi",
            "firstDay": 1,
            "height": "auto",
            "contentHeight": "auto",
            "expandRows": False,
            "eventDisplay": "block",
            "displayEventTime": False,
            "dayMaxEventRows": False,
            "eventMaxStack": 50,
            "fixedWeekCount": False,
            "handleWindowResize": False
        },
        custom_css="""
        html, body {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important;
        }

        .fc { font-family: Arial, sans-serif !important; color:#111827 !important; }

        @media (max-width: 768px) {
            html, body {
                width: 1400px !important;
                min-width: 1400px !important;
                overflow-x: auto !important;
            }

            .fc,
            .fc-view-harness,
            .fc-scrollgrid,
            .fc-scrollgrid table,
            .fc-col-header,
            .fc-daygrid-body,
            .fc-daygrid-body table {
                width: 1400px !important;
                min-width: 1400px !important;
            }

            .fc-daygrid-day {
                min-width: 190px !important;
            }

            .fc-daygrid-day-frame {
                min-height: 135px !important;
            }

            .fc-daygrid-week:has(.fc-daygrid-event) .fc-daygrid-day-frame,
            .fc-scrollgrid-sync-table tr:has(.fc-daygrid-event) .fc-daygrid-day-frame {
                min-height: 190px !important;
            }

            .fc-event-title {
                font-size: 12px !important;
                line-height: 1.28 !important;
            }

            .fc-toolbar {
                flex-wrap: nowrap !important;
                gap: 8px !important;
            }

            .fc-toolbar-title {
                font-size: 22px !important;
                white-space: nowrap !important;
            }
        }
        .fc-toolbar-title { font-size: 28px !important; font-weight: 800 !important; color:#111827 !important; }
        .fc-col-header-cell-cushion, .fc-daygrid-day-number { color:#111827 !important; font-weight:800 !important; }

        /* Hàng không có sự kiện co thấp lại. Hàng có sự kiện vẫn đủ cao để đọc nội dung. */
        .fc-daygrid-day-frame { min-height: 58px !important; height: auto !important; padding: 2px !important; }
        .fc-daygrid-week:has(.fc-daygrid-event) .fc-daygrid-day-frame,
        .fc-scrollgrid-sync-table tr:has(.fc-daygrid-event) .fc-daygrid-day-frame {
            min-height: 165px !important;
        }

        .fc-daygrid-day-events { min-height: 1px !important; margin-bottom: 4px !important; }
        .fc-daygrid-event-harness { position: relative !important; margin-top: 4px !important; }
        .fc-daygrid-event { white-space: normal !important; overflow: visible !important; padding: 5px 6px !important; border-radius: 6px !important; border-width: 0 0 0 5px !important; box-shadow: 0 1px 2px rgba(0,0,0,0.08) !important; }
        .fc-event-main { white-space: normal !important; overflow: visible !important; }
        .fc-event-title-container { white-space: normal !important; overflow: visible !important; }
        .fc-event-title { white-space: pre-line !important; overflow: visible !important; text-overflow: unset !important; line-height: 1.35 !important; font-size: 13px !important; font-weight: 700 !important; color:#111827 !important; font-family: Arial, sans-serif !important; }
        .fc-daygrid-block-event .fc-event-title { white-space: pre-line !important; }
        """
    )

    st.markdown("</div></div>", unsafe_allow_html=True)

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

# ================= BÁO CÁO =================
elif menu == "Báo cáo":
    st.subheader("📊 Báo cáo sự kiện theo đơn vị")

    st.markdown(
        '<div style="font-size:13px;font-weight:700;margin-bottom:6px;">Chọn kỳ báo cáo</div>',
        unsafe_allow_html=True
    )
    report_period = st.radio(
        "Chọn kỳ báo cáo",
        ["Tuần", "Tháng", "Năm"],
        index=1,
        horizontal=True,
        label_visibility="collapsed"
    )

    df_report, report_label, _, _ = get_period_df(df_f, report_period)
    st.markdown(
        f'<div style="font-size:13px;font-weight:700;margin-top:8px;">Báo cáo: {report_label}</div>',
        unsafe_allow_html=True
    )

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
            height=max(540, 52 * len(summary) + 180),
            hover_data={"donvi": True, "Đơn vị hiển thị": False}
        )

        fig.update_traces(
            textposition="outside",
            textfont=dict(size=16, color="black", family="Arial Black")
        )

        fig.update_layout(
            title=dict(text="", font=dict(size=1), x=0),
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=30, r=90, t=0, b=40),
            xaxis=dict(title="Số sự kiện", tickfont=dict(size=16, color="black", family="Arial Black"), title_font=dict(size=17, color="black", family="Arial Black")),
            yaxis=dict(title="", tickfont=dict(size=16, color="black", family="Arial Black"), automargin=True)
        )

        st.plotly_chart(fig, use_container_width=True)

        table_report = summary[["donvi", "Số sự kiện"]].sort_values("Số sự kiện", ascending=False)
        table_report = table_report.rename(columns={"donvi": "Đơn vị"}).reset_index(drop=True)
        table_report.insert(0, "STT", range(1, len(table_report) + 1))
        show_table_with_download(
            f"Bảng báo cáo sự kiện theo đơn vị - {report_label}",
            table_report,
            f"bao_cao_su_kien_{report_period.lower()}.xlsx",
            compact=True
        )

# ================= CẢNH BÁO =================
elif menu == "Cảnh báo":
    st.subheader("⚠️ Trùng lịch")

    df_check = df_f[(df_f["start"] >= today) & (df_f["start"] <= today + timedelta(days=30))].copy()
    found = False
    rows = []

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

                rows.append({
                    "Sự kiện 1": df_check.iloc[i]["event"],
                    "Thời gian 1": time_str_1,
                    "Địa điểm 1": loc1,
                    "Sự kiện 2": df_check.iloc[j]["event"],
                    "Thời gian 2": time_str_2,
                    "Địa điểm 2": loc2
                })

    if not found:
        st.success("Không phát hiện lịch bị trùng trong 30 ngày tới")
    else:
        show_table_with_download(
            "Bảng chi tiết lịch trùng/chồng lấn",
            pd.DataFrame(rows),
            "canh_bao_trung_lich.xlsx"
        )

# ================= HỖ TRỢ =================
elif menu == "Hỗ trợ":
    st.subheader("🛠️ Thống kê hoạt động cần hỗ trợ")

    st.markdown('<div class="table-title">Chọn kỳ thống kê hỗ trợ</div>', unsafe_allow_html=True)
    support_period = st.radio(
        "Chọn kỳ thống kê hỗ trợ",
        ["Tuần", "Tháng", "Năm"],
        index=1,
        horizontal=True,
        label_visibility="collapsed"
    )

    df_support_period, support_label, _, _ = get_period_df(df_f, support_period)
    support_table = build_support_table(df_support_period)

    if len(support_table) == 0:
        st.info("Không có thông tin cần hỗ trợ")
    else:
        # Sắp xếp theo thời gian giảm dần: sự kiện gần nhất/mới nhất ở trên cùng.
        support_table["_sort_time"] = pd.to_datetime(
            support_table["Ngày giờ"],
            format="%d/%m/%Y %H:%M",
            errors="coerce"
        )

        support_table = (
            support_table
            .sort_values(
                ["_sort_time", "Đơn vị", "Sự kiện", "Nội dung hỗ trợ"],
                ascending=[False, True, True, True]
            )
            .drop(columns=["_sort_time"])
            .reset_index(drop=True)
        )

        display_support_table = collapse_repeated_support_rows(support_table)
        show_table_with_download(
            f"Bảng sự kiện cần hỗ trợ - {support_label}",
            display_support_table,
            f"su_kien_can_ho_tro_{support_period.lower()}.xlsx"
        )

# ================= TRUY VẤN AI =================
elif menu == "Truy vấn AI":
    st.subheader("🤖 Truy vấn AI")
    q = st.text_input("Nhập câu hỏi, ví dụ: tuần, tháng, năm, hỗ trợ")

    if q:
        q = q.lower()

        if "tuần" in q:
            week_df, label, _, _ = get_period_df(df_f, "Tuần")
            show_table_with_download(f"Sự kiện {label}", build_event_query_table(week_df), "su_kien_tuan.xlsx")

        elif "tháng" in q:
            month_df, label, _, _ = get_period_df(df_f, "Tháng")
            show_table_with_download(f"Sự kiện {label}", build_event_query_table(month_df), "su_kien_thang.xlsx")

        elif "năm" in q:
            year_df, label, _, _ = get_period_df(df_f, "Năm")
            show_table_with_download(f"Sự kiện {label}", build_event_query_table(year_df), "su_kien_nam.xlsx")

        elif "hỗ trợ" in q or "ho tro" in q:
            # Chỉ lấy dữ liệu của năm hiện hành
            support_year_df = df_f[df_f["start"].dt.year == today.year]
            support_df = build_support_table(support_year_df)

            if len(support_df) == 0:
                st.info("Không có thông tin cần hỗ trợ")
            else:
                support_df["_sort_time"] = pd.to_datetime(
                    support_df["Ngày giờ"],
                    format="%d/%m/%Y %H:%M",
                    errors="coerce"
                )

                support_df = (
                    support_df
                    .sort_values(
                        ["_sort_time", "Đơn vị", "Sự kiện", "Nội dung hỗ trợ"],
                        ascending=[True, True, True, True]
                    )
                    .drop(columns=["_sort_time"])
                    .reset_index(drop=True)
                )

                support_display = collapse_repeated_support_rows(support_df)
                show_table_with_download("Danh sách sự kiện cần hỗ trợ", support_display, "danh_sach_can_ho_tro.xlsx")

        else:
            st.warning("Không hiểu yêu cầu. Hãy nhập: tuần, tháng, năm hoặc hỗ trợ")

# ================= PHÊ DUYỆT =================
elif menu == "Phê duyệt":
    st.subheader("📋 Sự kiện cần phê duyệt")
    st.info("Bảng rút gọn từ dữ liệu gốc để quản trị viên biết sự kiện cần vào hệ thống đăng ký phê duyệt.")

    approval_table = build_approval_summary_table(df_month)

    show_table_with_download(
        "Bảng sự kiện cần phê duyệt",
        approval_table,
        "su_kien_can_phe_duyet.xlsx"
    )

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
