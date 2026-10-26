"""Pulse Sales Lab — a lightweight sales visualization web app.

Built with Python's standard library, Pandas and Matplotlib. No notebook or web framework required.
"""
from __future__ import annotations

import html
import io
import os
import re
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TEMPLATE_PATH = BASE_DIR / "templates" / "index.html"
CSS_PATH = BASE_DIR / "static" / "style.css"
CHART_DIR = BASE_DIR / "static" / "charts"
SAMPLE_PATH = DATA_DIR / "sales_data.csv"
UPLOAD_PATH = DATA_DIR / "uploaded_sales.csv"
HOST = "127.0.0.1"
PORT = 8000

DATA_DIR.mkdir(exist_ok=True)
CHART_DIR.mkdir(parents=True, exist_ok=True)
ACTIVE_DATA_PATH = UPLOAD_PATH if UPLOAD_PATH.exists() else SAMPLE_PATH
DATA_LOCK = threading.Lock()

# Accept common column headings from classroom and Superstore-style sales CSV files.
COLUMN_ALIASES = {
    "date": "Date", "order date": "Date", "order_date": "Date", "orderdate": "Date",
    "sales date": "Date", "transaction date": "Date", "invoice date": "Date",
    "category": "Category", "product category": "Category", "product_category": "Category",
    "sub-category": "Category", "sub category": "Category", "sub_category": "Category",
    "sales": "Sales", "total sales": "Sales", "revenue": "Sales", "amount": "Sales",
    "sales amount": "Sales", "total": "Sales", "net sales": "Sales",
    "product": "Product", "product name": "Product", "product_name": "Product",
    "item": "Product", "item name": "Product", "item_name": "Product",
    "profit": "Profit", "net profit": "Profit", "margin value": "Profit",
    "quantity": "Quantity", "qty": "Quantity", "units": "Quantity", "units sold": "Quantity",
    "region": "Region", "sales region": "Region", "area": "Region", "market": "Region",
}


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize common column names and validate the minimum needed for charts."""
    if df.empty:
        raise ValueError("The CSV has no data rows. Add at least one sales record and try again.")

    rename_map = {}
    seen_targets = set()
    for column in df.columns:
        clean = re.sub(r"\s+", " ", str(column).strip().lower())
        target = COLUMN_ALIASES.get(clean)
        if target and target not in seen_targets:
            rename_map[column] = target
            seen_targets.add(target)
    df = df.rename(columns=rename_map).copy()

    if "Sales" not in df.columns:
        raise ValueError("Couldn't find a Sales column. Use a heading such as Sales, Revenue, or Amount.")
    if "Date" not in df.columns:
        raise ValueError("Couldn't find a Date column. Use a heading such as Date or Order Date.")

    # Helpful defaults keep the dashboard useful when a dataset only has date and sales.
    if "Category" not in df.columns:
        df["Category"] = "Uncategorized"
    if "Product" not in df.columns:
        df["Product"] = [f"Item {i + 1}" for i in range(len(df))]
    if "Profit" not in df.columns:
        df["Profit"] = 0
    if "Quantity" not in df.columns:
        df["Quantity"] = 1
    if "Region" not in df.columns:
        df["Region"] = "Not specified"

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Sales"] = pd.to_numeric(df["Sales"].astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")
    df["Profit"] = pd.to_numeric(df["Profit"].astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce").fillna(0)
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(1)
    df["Category"] = df["Category"].fillna("Uncategorized").astype(str).str.strip().replace("", "Uncategorized")
    df["Product"] = df["Product"].fillna("Unknown item").astype(str).str.strip().replace("", "Unknown item")
    df["Region"] = df["Region"].fillna("Not specified").astype(str).str.strip().replace("", "Not specified")
    df = df.dropna(subset=["Date", "Sales"])
    if df.empty:
        raise ValueError("No valid records found. Make sure Date values are dates and Sales values are numbers.")
    df["Quantity"] = df["Quantity"].clip(lower=0)
    return df.sort_values("Date").reset_index(drop=True)


def load_data(path: Path | None = None) -> pd.DataFrame:
    path = path or ACTIVE_DATA_PATH
    try:
        raw = pd.read_csv(path)
    except UnicodeDecodeError:
        raw = pd.read_csv(path, encoding="latin-1")
    return normalize_dataframe(raw)


def money(value: float) -> str:
    return "₹" + format(float(value), ",.0f")


def make_charts(df: pd.DataFrame) -> None:
    """Generate a category bar chart and a monthly sales trend line chart."""
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.labelcolor": "#65718a",
        "xtick.color": "#8a94a8",
        "ytick.color": "#8a94a8",
        "text.color": "#17233c",
    })
    panel = "#ffffff"
    grid = "#e9edf4"
    teal = "#20b99b"
    purple = "#7867f5"

    by_category = df.groupby("Category", dropna=False)["Sales"].sum().sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(7.6, 3.1), dpi=130)
    fig.patch.set_facecolor(panel)
    ax.set_facecolor(panel)
    bar_colors = ["#b9b3ff" if i < len(by_category) - 1 else purple for i in range(len(by_category))]
    bars = ax.barh(by_category.index.astype(str), by_category.values, color=bar_colors, height=0.58)
    ax.set_xlabel("Sales (INR)", labelpad=10, fontsize=9)
    ax.grid(axis="x", color=grid, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(grid)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.tick_params(axis="x", length=0, pad=7)
    max_value = max(float(by_category.max()) if len(by_category) else 0, 1)
    ax.set_xlim(0, max_value * 1.22)
    for bar, value in zip(bars, by_category.values):
        ax.text(value + max_value * 0.02, bar.get_y() + bar.get_height() / 2,
                f"₹{value:,.0f}", va="center", ha="left", fontsize=8, color="#46536c")
    fig.tight_layout(pad=1.5)
    fig.savefig(CHART_DIR / "category_sales.png", facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)

    monthly = df.assign(Month=df["Date"].dt.to_period("M")).groupby("Month")["Sales"].sum().sort_index()
    labels = [period.strftime("%b %y") for period in monthly.index.to_timestamp()]
    values = monthly.values
    fig, ax = plt.subplots(figsize=(7.6, 3.1), dpi=130)
    fig.patch.set_facecolor(panel)
    ax.set_facecolor(panel)
    x = list(range(len(values)))
    ax.fill_between(x, values, [0] * len(values), color=teal, alpha=0.09)
    ax.plot(x, values, color=teal, linewidth=2.6, marker="o", markersize=5,
            markerfacecolor="#ffffff", markeredgewidth=2, markeredgecolor=teal)
    if len(values) > 0:
        peak_i = int(values.argmax())
        ax.scatter([peak_i], [values[peak_i]], color=purple, s=42, zorder=4)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=0 if len(labels) <= 8 else 35, ha="right" if len(labels) > 8 else "center")
    ax.set_ylabel("Sales (INR)", labelpad=10, fontsize=9)
    ax.grid(axis="y", color=grid, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(grid)
    ax.tick_params(axis="both", length=0, pad=8)
    ax.margins(x=0.04, y=0.22)
    fig.tight_layout(pad=1.5)
    fig.savefig(CHART_DIR / "monthly_sales.png", facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def make_html(df: pd.DataFrame, error: str = "") -> bytes:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    total_sales = float(df["Sales"].sum())
    total_profit = float(df["Profit"].sum())
    total_units = float(df["Quantity"].sum())
    avg_order = total_sales / max(len(df), 1)
    category_sales = df.groupby("Category")["Sales"].sum().sort_values(ascending=False)
    monthly = df.assign(Month=df["Date"].dt.to_period("M")).groupby("Month")["Sales"].sum().sort_values(ascending=False)
    region_sales = df.groupby("Region")["Sales"].sum().sort_values(ascending=False)
    top_category = str(category_sales.index[0]) if len(category_sales) else "—"
    top_category_value = float(category_sales.iloc[0]) if len(category_sales) else 0
    best_month = monthly.index[0].strftime("%B %Y") if len(monthly) else "—"
    best_month_value = float(monthly.iloc[0]) if len(monthly) else 0
    top_region = str(region_sales.index[0]) if len(region_sales) else "—"
    date_min = df["Date"].min().strftime("%b %Y")
    date_max = df["Date"].max().strftime("%b %Y")
    source_name = "Uploaded CSV" if ACTIVE_DATA_PATH == UPLOAD_PATH else "Sample sales dataset"
    profit_margin = total_profit / total_sales * 100 if total_sales else 0

    transaction_rows = []
    for _, row in df.sort_values("Date", ascending=False).head(7).iterrows():
        transaction_rows.append(
            "<tr>"
            f"<td><span class=\"date-dot\"></span>{html.escape(row['Date'].strftime('%d %b %Y'))}</td>"
            f"<td><span class=\"product-name\">{html.escape(str(row['Product']))}</span></td>"
            f"<td><span class=\"category-chip\">{html.escape(str(row['Category']))}</span></td>"
            f"<td>{html.escape(str(row['Region']))}</td>"
            f"<td class=\"amount\">{money(row['Sales'])}</td>"
            "</tr>"
        )
    if not transaction_rows:
        transaction_rows.append('<tr><td colspan="5" class="empty-cell">No records to preview.</td></tr>')

    insight_text = (
        f"<div class=\"insight-icon purple\">↗</div><div><div class=\"insight-title\">{html.escape(top_category)} leads sales</div>"
        f"<p>It contributes <strong>{money(top_category_value)}</strong>, the highest total among categories.</p></div>"
        f"<div class=\"insight-icon mint\">◷</div><div><div class=\"insight-title\">{html.escape(best_month)} was the strongest month</div>"
        f"<p>Sales reached <strong>{money(best_month_value)}</strong> in this period.</p></div>"
        f"<div class=\"insight-icon gold\">⌖</div><div><div class=\"insight-title\">{html.escape(top_region)} is the top region</div>"
        f"<p>It generated the largest regional sales total in the current dataset.</p></div>"
    )

    replacements = {
        "{{TOTAL_SALES}}": money(total_sales),
        "{{TOTAL_PROFIT}}": money(total_profit),
        "{{TOTAL_UNITS}}": f"{total_units:,.0f}",
        "{{AVG_ORDER}}": money(avg_order),
        "{{PROFIT_MARGIN}}": f"{profit_margin:.1f}%",
        "{{ROW_COUNT}}": f"{len(df):,}",
        "{{CATEGORY_COUNT}}": f"{df['Category'].nunique():,}",
        "{{DATE_RANGE}}": f"{date_min} – {date_max}",
        "{{SOURCE_NAME}}": html.escape(source_name),
        "{{TRANSACTION_ROWS}}": "\n".join(transaction_rows),
        "{{INSIGHTS}}": insight_text,
        "{{ERROR_MESSAGE}}": f'<div class="notice error">{html.escape(error)}</div>' if error else "",
        "{{CHART_VERSION}}": str(int(time.time())),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template.encode("utf-8")


def read_uploaded_file(body: bytes, content_type: str) -> bytes:
    """Extract a CSV file part from a browser multipart upload without extra libraries."""
    match = re.search(r"boundary=(?:\"([^\"]+)\"|([^;]+))", content_type)
    if not match:
        raise ValueError("The upload form was not recognized. Please choose a CSV file and try again.")
    boundary = (match.group(1) or match.group(2)).encode("utf-8")
    for part in body.split(b"--" + boundary):
        if b"Content-Disposition" not in part or b"filename=" not in part:
            continue
        header_blob, separator, payload = part.partition(b"\r\n\r\n")
        if not separator:
            continue
        disposition = header_blob.decode("latin-1", errors="ignore")
        filename_match = re.search(r'filename="([^\"]*)"', disposition)
        filename = filename_match.group(1) if filename_match else "upload.csv"
        if not filename.lower().endswith(".csv"):
            raise ValueError("Please upload a .csv file. Excel files (.xlsx) are not supported by this task app.")
        payload = payload.rstrip(b"\r\n")
        if not payload:
            raise ValueError("That CSV file appears to be empty.")
        return payload
    raise ValueError("Please choose a CSV file before clicking Analyze CSV.")


class SalesDashboardHandler(BaseHTTPRequestHandler):
    server_version = "PulseSalesLab/1.0"

    def log_message(self, format_string, *args):
        print("[web] " + format_string % args)

    def send_bytes(self, body: bytes, content_type: str, status: int = 200, extra_headers: dict | None = None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location: str):
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        global ACTIVE_DATA_PATH
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        if path == "/":
            with DATA_LOCK:
                df = load_data(ACTIVE_DATA_PATH)
                make_charts(df)
                error = params.get("error", [""])[0]
                content = make_html(df, error=error)
            self.send_bytes(content, "text/html; charset=utf-8")
        elif path == "/static/style.css":
            self.send_bytes(CSS_PATH.read_bytes(), "text/css; charset=utf-8")
        elif path == "/charts/category_sales.png":
            chart = CHART_DIR / "category_sales.png"
            if not chart.exists():
                make_charts(load_data())
            self.send_bytes(chart.read_bytes(), "image/png")
        elif path == "/charts/monthly_sales.png":
            chart = CHART_DIR / "monthly_sales.png"
            if not chart.exists():
                make_charts(load_data())
            self.send_bytes(chart.read_bytes(), "image/png")
        elif path == "/download-sample.csv":
            self.send_bytes(SAMPLE_PATH.read_bytes(), "text/csv; charset=utf-8", extra_headers={
                "Content-Disposition": 'attachment; filename="sales_data.csv"'
            })
        elif path == "/favicon.ico":
            self.send_bytes(b"", "image/x-icon", status=204)
        else:
            self.send_bytes(b"Page not found", "text/plain; charset=utf-8", status=404)

    def do_POST(self):
        global ACTIVE_DATA_PATH
        parsed = urlparse(self.path)
        if parsed.path == "/reset":
            with DATA_LOCK:
                ACTIVE_DATA_PATH = SAMPLE_PATH
                try:
                    UPLOAD_PATH.unlink(missing_ok=True)
                except OSError:
                    pass
            self.redirect("/")
            return
        if parsed.path != "/upload":
            self.send_bytes(b"Not found", "text/plain; charset=utf-8", status=404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 15 * 1024 * 1024:
                raise ValueError("Choose a CSV file under 15 MB.")
            payload = read_uploaded_file(self.rfile.read(length), self.headers.get("Content-Type", ""))
            # Validate in memory before replacing the user's active view.
            try:
                raw = pd.read_csv(io.BytesIO(payload))
            except UnicodeDecodeError:
                raw = pd.read_csv(io.BytesIO(payload), encoding="latin-1")
            normalize_dataframe(raw)
            with DATA_LOCK:
                UPLOAD_PATH.write_bytes(payload)
                ACTIVE_DATA_PATH = UPLOAD_PATH
            self.redirect("/")
        except Exception as exc:
            self.redirect("/?error=" + __import__("urllib.parse", fromlist=["quote"]).quote(str(exc)))


def main() -> None:
    global ACTIVE_DATA_PATH
    ACTIVE_DATA_PATH = UPLOAD_PATH if UPLOAD_PATH.exists() else SAMPLE_PATH
    try:
        with DATA_LOCK:
            make_charts(load_data(ACTIVE_DATA_PATH))
    except Exception as exc:
        print(f"Could not build initial charts: {exc}")
        raise
    server = ThreadingHTTPServer((HOST, PORT), SalesDashboardHandler)
    print("\n  PULSE SALES LAB is running")
    print(f"  Open your browser at: http://{HOST}:{PORT}")
    print("  Stop the server with Ctrl + C in this terminal.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped. You can close this terminal window.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
