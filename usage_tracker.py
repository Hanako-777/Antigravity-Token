import base64
import glob
import json
import os
import sys
import urllib.request
import webbrowser
from datetime import datetime, timedelta
from collections import defaultdict

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_HTML = os.path.join(APP_DIR, "usage_dashboard.html")

def get_user_profile():
    creds_path = os.path.expanduser(r"~\.gemini\oauth_creds.json")
    user_name = ""
    user_email = ""
    avatar_url = ""

    if os.path.exists(creds_path):
        try:
            with open(creds_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            id_token = data.get("id_token", "")
            if id_token and "." in id_token:
                parts = id_token.split(".")
                if len(parts) >= 2:
                    payload_b64 = parts[1]
                    payload_b64 += "=" * (-len(payload_b64) % 4)
                    payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
                    user_name = payload.get("name") or ""
                    user_email = payload.get("email") or ""
                    avatar_url = payload.get("picture") or ""
        except Exception:
            pass

    raw_email = user_email
    if not user_email:
        acc_path = os.path.expanduser(r"~\.gemini\google_accounts.json")
        if os.path.exists(acc_path):
            try:
                with open(acc_path, "r", encoding="utf-8") as f:
                    acc_data = json.load(f)
                    user_email = acc_data.get("active", "")
                    raw_email = user_email
            except Exception:
                pass

    if not user_name:
        if user_email and "@" in user_email:
            user_name = user_email.split("@")[0].capitalize()
        else:
            user_name = os.environ.get("USERNAME", "Antigravity User")

    handle = f"@{user_email.split('@')[0]}" if user_email and "@" in user_email else f"@{user_name.lower().replace(' ', '')}"

    avatar_b64 = ""
    if avatar_url:
        if "=s96-c" in avatar_url:
            avatar_url = avatar_url.replace("=s96-c", "=s192-c")
        cache_file = os.path.join(APP_DIR, ".user_avatar.cache")
        try:
            if os.path.exists(cache_file) and (datetime.now().timestamp() - os.path.getmtime(cache_file) < 86400 * 7):
                with open(cache_file, "r", encoding="utf-8") as cf:
                    avatar_b64 = cf.read().strip()
            else:
                req = urllib.request.Request(avatar_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    raw_bytes = resp.read()
                    mime = resp.headers.get_content_type() or "image/png"
                    avatar_b64 = f"data:{mime};base64,{base64.b64encode(raw_bytes).decode('utf-8')}"
                    with open(cache_file, "w", encoding="utf-8") as cf:
                        cf.write(avatar_b64)
        except Exception:
            pass

    initial = user_name[0].upper() if user_name else "A"
    return {
        "name": user_name,
        "handle": handle,
        "email": raw_email or "Local User",
        "avatar_b64": avatar_b64,
        "avatar_url": avatar_url,
        "initial": initial
    }


def analyze_usage():
    daily = defaultdict(lambda: {"input": 0, "output": 0, "cache": 0, "turns": 0})
    total = {"input": 0, "output": 0, "cache": 0, "turns": 0}

    # 1. 优先读取完整同步缓存（由 tokscale/Token Monitor 生成，包含完整的会话历史调用）
    tokscale_sessions_dir = os.path.expandvars(r"%APPDATA%\tokscale\antigravity-cache\sessions")
    tokscale_files = glob.glob(os.path.join(tokscale_sessions_dir, "*.jsonl")) if os.path.exists(tokscale_sessions_dir) else []

    if tokscale_files:
        for f in tokscale_files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    for line in fp:
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            if data.get("type") == "usage":
                                inp = data.get("input", 0) or 0
                                out = data.get("output", 0) or 0
                                cache = data.get("cacheRead", 0) or 0
                                ts = data.get("timestamp")
                                date_str = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d") if ts else "Unknown"

                                daily[date_str]["input"] += inp
                                daily[date_str]["output"] += out
                                daily[date_str]["cache"] += cache
                                daily[date_str]["turns"] += 1

                                total["input"] += inp
                                total["output"] += out
                                total["cache"] += cache
                                total["turns"] += 1
                        except Exception:
                            pass
            except Exception:
                pass
        return daily, total

    # 2. 原生兜底方案：扫描本地 brain/*/transcript.jsonl 记录
    brain_dir = os.path.expanduser(r"~\.gemini\antigravity\brain")
    files = glob.glob(os.path.join(brain_dir, "*", ".system_generated", "logs", "transcript.jsonl"))

    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                for line in fp:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        inp = data.get("input_tokens", 0) or 0
                        out = data.get("output_tokens", 0) or 0
                        cache = data.get("cache_read_tokens", 0) or 0
                        created = data.get("created_at", "")
                        msg_type = data.get("type", "")

                        if inp > 0 or out > 0 or cache > 0 or msg_type == "PLANNER_RESPONSE":
                            date_str = created[:10] if created else "Unknown"
                            daily[date_str]["input"] += inp
                            daily[date_str]["output"] += out
                            daily[date_str]["cache"] += cache
                            daily[date_str]["turns"] += 1

                            total["input"] += inp
                            total["output"] += out
                            total["cache"] += cache
                            total["turns"] += 1
                    except Exception:
                        pass
        except Exception:
            pass

    return daily, total

def format_tokens(num):
    if num >= 100000000:
        return f"{num / 100000000:.2f}亿"
    if num >= 10000:
        return f"{num / 10000:.1f}万"
    return f"{num:,}"

def generate_heatmap_52_weeks(daily):
    today = datetime.now().date()
    start_date = today - timedelta(days=52 * 7 + (today.weekday() + 1) % 7)
    
    weeks = []
    curr = start_date
    col_idx = 0

    while curr <= today:
        current_week = []
        for row_idx in range(7):
            d_str = curr.strftime("%Y-%m-%d")
            item = daily.get(d_str, None)
            tokens = (item["input"] + item["output"] + item.get("cache", 0)) if item else 0
            current_week.append({
                "date": d_str,
                "tokens": tokens,
                "input": item["input"] if item else 0,
                "output": item["output"] if item else 0,
                "cache": item["cache"] if item else 0,
                "turns": item["turns"] if item else 0,
                "col": col_idx,
                "row": row_idx,
                "month": curr.month,
                "day": curr.day
            })
            curr += timedelta(days=1)
            if curr > today:
                break
        weeks.append(current_week)
        col_idx += 1

    return weeks

def build_codex_style_html(daily, total):
    grand_total_tokens = total["input"] + total["output"] + total.get("cache", 0)
    dates = sorted(daily.keys())
    
    # Peak day
    peak_val = 0
    peak_date = "无"
    for d, item in daily.items():
        tot = item["input"] + item["output"] + item.get("cache", 0)
        if tot > peak_val:
            peak_val = tot
            peak_date = d

    # Today stats
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_item = daily.get(today_str, {"input": 0, "output": 0, "cache": 0, "turns": 0})
    today_tokens = today_item["input"] + today_item["output"] + today_item.get("cache", 0)

    # Active days
    active_days_count = len([d for d, item in daily.items() if (item["input"] + item["output"] + item.get("cache", 0) > 0 or item["turns"] > 0)])
    avg_per_active_day = int(grand_total_tokens / active_days_count) if active_days_count > 0 else 0

    # User profile (Codex style)
    profile = get_user_profile()
    avatar_src = profile["avatar_b64"] or profile["avatar_url"]
    if avatar_src:
        avatar_html = f'''<img class="avatar-img" src="{avatar_src}" alt="{profile['name']}" onerror="this.style.display=\\'none\\'; this.nextElementSibling.style.display=\\'flex\\';">
                <div class="avatar-fallback" style="display:none;">{profile['initial']}</div>'''
    else:
        avatar_html = f'''<div class="avatar-fallback">{profile['initial']}</div>'''

    # Chart datasets
    chart_dates = []
    chart_inputs = []
    chart_outputs = []
    chart_caches = []
    cum_sum = 0
    chart_cumulative = []

    for d in dates:
        chart_dates.append(d[5:]) # MM-DD
        chart_inputs.append(daily[d]["input"])
        chart_outputs.append(daily[d]["output"])
        chart_caches.append(daily[d].get("cache", 0))
        day_tot = daily[d]["input"] + daily[d]["output"] + daily[d].get("cache", 0)
        cum_sum += day_tot
        chart_cumulative.append(cum_sum)

    # Weekly grouped data
    weeks_map = defaultdict(lambda: {"input": 0, "output": 0, "cache": 0, "total": 0})
    for d in dates:
        dt = datetime.strptime(d, "%Y-%m-%d")
        w_str = f"{dt.month}月第{((dt.day - 1) // 7) + 1}周"
        day_tot = daily[d]["input"] + daily[d]["output"] + daily[d].get("cache", 0)
        weeks_map[w_str]["input"] += daily[d]["input"]
        weeks_map[w_str]["output"] += daily[d]["output"]
        weeks_map[w_str]["cache"] += daily[d].get("cache", 0)
        weeks_map[w_str]["total"] += day_tot

    week_labels = sorted(weeks_map.keys())
    week_totals = [weeks_map[w]["total"] for w in week_labels]

    # Table rows
    table_rows = ""
    for d in reversed(dates):
        item = daily[d]
        tot = item["input"] + item["output"] + item.get("cache", 0)
        is_today_tag = '<span class="today-tag">今天</span>' if d == today_str else ''
        table_rows += f"""
        <tr>
            <td class="col-date">{d} {is_today_tag}</td>
            <td class="col-turns">{item['turns']} 轮</td>
            <td class="col-num">{item['input']:,}</td>
            <td class="col-num">{item['output']:,}</td>
            <td class="col-num col-muted">{item['cache']:,}</td>
            <td class="col-num col-total">{tot:,}</td>
        </tr>
        """

    weeks_data = generate_heatmap_52_weeks(daily)
    weeks_json = json.dumps(weeks_data)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Antigravity Token</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-page: #f8fafc;
            --bg-card: #ffffff;
            --border-color: #e2e8f0;
            --text-heading: #0f172a;
            --text-body: #334155;
            --text-subtle: #64748b;
            --text-muted: #94a3b8;
            --brand-blue: #2563eb;
            --control-bg: #f1f5f9;
            --heat-empty: #e2e8f0;
            --card-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.04);
        }}

        [data-theme="dark"] {{
            --bg-page: #0b0f19;
            --bg-card: #131b2e;
            --border-color: #1e293b;
            --text-heading: #f8fafc;
            --text-body: #cbd5e1;
            --text-subtle: #94a3b8;
            --text-muted: #64748b;
            --brand-blue: #38bdf8;
            --control-bg: #1e293b;
            --heat-empty: #1e293b;
            --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.25);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            transition: background-color 0.25s ease, border-color 0.25s ease, color 0.25s ease;
        }}

        /* Modern Sleek Scrollbar */
        ::-webkit-scrollbar {{
            width: 5px;
            height: 5px;
        }}
        ::-webkit-scrollbar-track {{
            background: transparent;
        }}
        ::-webkit-scrollbar-thumb {{
            background: var(--border-color);
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: var(--text-muted);
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", "Helvetica Neue", Arial, sans-serif;
            background-color: var(--bg-page);
            color: var(--text-body);
            padding: 16px 20px 36px;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
            overflow-x: hidden;
            overflow-y: auto;
        }}

        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}

        /* Navbar */
        .navbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 14px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
            gap: 8px;
            min-width: 0;
        }}

        .brand-group {{
            display: flex;
            align-items: center;
            gap: 8px;
            min-width: 0;
            flex-shrink: 1;
        }}

        .brand-name {{
            font-size: 15px;
            font-weight: 600;
            letter-spacing: -0.01em;
            color: var(--text-heading);
            white-space: nowrap;
        }}

        .nav-tools {{
            display: flex;
            align-items: center;
            gap: 6px;
            flex-shrink: 0;
        }}

        .user-pill {{
            padding: 3px 8px;
            border-radius: 20px;
            background: var(--control-bg);
            border: 1px solid var(--border-color);
            font-size: 11px;
            font-weight: 500;
            color: var(--text-subtle);
            display: flex;
            align-items: center;
            gap: 4px;
            max-width: 140px;
        }}

        .user-pill span {{
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .icon-btn {{
            width: 28px;
            height: 28px;
            border-radius: 7px;
            border: 1px solid var(--border-color);
            background: var(--bg-card);
            color: var(--text-subtle);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            flex-shrink: 0;
        }}

        .icon-btn:hover {{
            background: var(--control-bg);
            color: var(--text-heading);
        }}

        .icon-btn.active {{
            background: rgba(59, 130, 246, 0.14);
            border-color: #3b82f6;
            color: #3b82f6;
        }}

        .icon-btn.active svg {{
            fill: rgba(59, 130, 246, 0.25);
        }}

        .svg-icon {{
            width: 14px;
            height: 14px;
            stroke-width: 1.8;
            stroke: currentColor;
            fill: none;
            stroke-linecap: round;
            stroke-linejoin: round;
        }}

        /* User Profile Hero (Codex Style) */
        .profile-section {{
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            margin: 4px 0 16px;
        }}

        .avatar-wrap {{
            position: relative;
            width: 72px;
            height: 72px;
            margin-bottom: 8px;
        }}

        .avatar-img {{
            width: 72px;
            height: 72px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid var(--border-color);
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.1);
            display: block;
        }}

        .avatar-fallback {{
            width: 72px;
            height: 72px;
            border-radius: 50%;
            background: linear-gradient(135deg, #2563eb, #ec4899);
            color: #ffffff;
            font-size: 28px;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
            border: 2px solid var(--border-color);
        }}

        .profile-name {{
            font-size: 19px;
            font-weight: 650;
            color: var(--text-heading);
            line-height: 1.25;
            letter-spacing: -0.01em;
        }}

        .profile-handle {{
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 3px;
            font-family: inherit;
        }}

        /* Codex 5-Metrics Hero Bar */
        .codex-bar {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 14px 16px;
            display: grid;
            grid-template-columns: 1fr 1fr 1.25fr 0.9fr 1fr;
            margin-bottom: 16px;
            box-shadow: var(--card-shadow);
            min-width: 0;
        }}

        .codex-col {{
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            padding: 2px 6px;
            min-width: 0;
        }}

        .codex-col:not(:last-child) {{
            border-right: 1px solid var(--border-color);
        }}

        .codex-num {{
            font-size: 17.5px;
            font-weight: 600;
            letter-spacing: -0.01em;
            color: var(--text-heading);
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
        }}

        .codex-label {{
            font-size: 11px;
            color: var(--text-subtle);
            margin-top: 3px;
            font-weight: 400;
            white-space: nowrap;
        }}

        /* Section Headers */
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}

        .section-title {{
            font-size: 14px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
            color: var(--text-heading);
        }}

        .seg-control {{
            display: inline-flex;
            background: var(--control-bg);
            padding: 2px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            gap: 2px;
        }}

        .seg-btn {{
            padding: 3px 10px;
            border-radius: 5px;
            border: none;
            background: transparent;
            font-size: 11.5px;
            font-weight: 500;
            color: var(--text-subtle);
            cursor: pointer;
            transition: all 0.2s ease;
        }}

        .seg-btn:hover {{ color: var(--text-heading); }}

        .seg-btn.active {{
            background: var(--bg-card);
            color: var(--text-heading);
            font-weight: 600;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }}

        /* Card Container */
        .card-container {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px 18px;
            margin-bottom: 16px;
            box-shadow: var(--card-shadow);
            position: relative;
            overflow: hidden !important;
        }}

        /* Activity Heatmap Layout */
        .activity-full-wrapper {{
            width: 100%;
            overflow: hidden !important;
            position: relative;
            min-height: 180px;
        }}

        .month-labels-row {{
            display: flex;
            justify-content: space-between;
            padding: 0 4px 6px 4px;
            font-size: 11px;
            color: var(--text-muted);
            user-select: none;
        }}

        .month-labels-row.mobile-only {{
            display: none;
        }}

        .heatmap-grid-scroll {{
            display: grid;
            grid-template-columns: repeat(53, 1fr);
            gap: 4px;
            width: 100%;
            padding: 2px 0 8px;
            overflow: hidden !important;
        }}

        .heatmap-col {{
            display: grid;
            grid-template-rows: repeat(7, 1fr);
            gap: 3.5px;
        }}

        .heat-cell {{
            aspect-ratio: 1 / 1;
            width: 100%;
            border-radius: 2.5px;
            background-color: var(--heat-empty);
            cursor: pointer;
            opacity: 0;
            transform: scale(0.35) translate(-4px, -4px);
        }}

        /* Diagonal Ripple Wave Keyframes */
        @keyframes diagonalAppear {{
            0% {{
                opacity: 0;
                transform: scale(0.35) translate(-4px, -4px);
            }}
            100% {{
                opacity: 1;
                transform: scale(1) translate(0, 0);
            }}
        }}

        .heat-cell.animated {{
            animation: diagonalAppear 0.42s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }}

        .heat-cell:hover {{
            outline: 2px solid var(--brand-blue);
            outline-offset: 1px;
            z-index: 5;
        }}

        /* Activity Bottom Bar */
        .activity-bottom-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 12px;
            padding-top: 10px;
            border-top: 1px solid var(--border-color);
            font-size: 11.5px;
            color: var(--text-subtle);
        }}

        .activity-audit-tags {{
            display: flex;
            gap: 14px;
        }}

        .audit-tag-item {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}

        .audit-tag-val {{
            font-weight: 600;
            color: var(--text-heading);
            font-variant-numeric: tabular-nums;
        }}

        .heat-legend-group {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 11px;
            color: var(--text-muted);
        }}

        .legend-squares {{
            display: flex;
            gap: 3px;
        }}

        .legend-sq {{
            width: 9px;
            height: 9px;
            border-radius: 2px;
        }}

        /* Antigravity Tools 6-Grid Stats - CENTERED */
        .stats-6-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 16px;
        }}

        .stat-card-box {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 14px 14px;
            box-shadow: var(--card-shadow);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }}

        .stat-card-head {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            font-size: 11.5px;
            font-weight: 500;
            color: var(--text-subtle);
            margin-bottom: 6px;
        }}

        .stat-card-num {{
            font-size: 20px;
            font-weight: 600;
            letter-spacing: -0.01em;
            color: var(--text-heading);
            font-variant-numeric: tabular-nums;
        }}

        .stat-card-sub {{
            font-size: 10.5px;
            color: var(--text-muted);
            margin-top: 2px;
        }}

        /* Chart Panes */
        #heatmapPane {{
            display: block;
            width: 100%;
        }}

        #altChartPane {{
            display: none;
            width: 100%;
            height: 180px;
        }}

        .chart-wrapper {{
            height: 230px;
            margin-top: 6px;
            overflow: hidden !important;
        }}

        /* Clean Table */
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}

        th, td {{
            padding: 9px 12px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}

        th {{
            font-weight: 500;
            color: var(--text-subtle);
            font-size: 10.5px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            background: var(--control-bg);
            border-top: 1px solid var(--border-color);
        }}

        tr:hover td {{
            background: rgba(37, 99, 235, 0.02);
        }}

        .col-date {{ font-weight: 500; color: var(--text-heading); }}
        .col-turns {{ color: var(--text-subtle); font-size: 11px; }}
        .col-num {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; color: var(--text-body); }}
        .col-muted {{ color: var(--text-muted); }}
        .col-total {{ color: var(--text-heading); font-weight: 600; }}

        .today-tag {{
            font-size: 9.5px;
            font-weight: 500;
            padding: 1px 4px;
            background: rgba(37, 99, 235, 0.1);
            color: var(--brand-blue);
            border-radius: 3px;
            margin-left: 4px;
        }}

        /* Floating Tooltip */
        #tooltip {{
            position: fixed;
            display: none;
            background: #0f172a;
            color: #f8fafc;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 11.5px;
            pointer-events: none;
            z-index: 9999;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
            border: 1px solid rgba(255, 255, 255, 0.12);
            line-height: 1.5;
            min-width: 175px;
        }}

        /* Responsive View for Medium & Compact Floating Windows */
        @media (max-width: 860px) {{
            body {{
                padding: 14px 18px 28px;
            }}

            /* 6-Grid Stats: 3 columns on medium */
            .stats-6-grid {{
                grid-template-columns: repeat(3, 1fr);
                gap: 10px;
            }}
            .stat-card-box {{
                padding: 12px 10px;
            }}

            /* Heatmap in HUD mode: show recent 28 weeks with crisp 15px tiles */
            .month-labels-row.desktop-only {{
                display: none;
            }}
            .month-labels-row.mobile-only {{
                display: flex;
            }}
            .heatmap-grid-scroll {{
                grid-template-columns: repeat(28, 1fr);
                gap: 4.5px;
            }}
            .heatmap-col:nth-child(-n+25) {{
                display: none;
            }}

            .activity-bottom-bar {{
                flex-direction: column;
                gap: 8px;
                align-items: center;
            }}
            .activity-audit-tags {{
                justify-content: space-between;
                width: 100%;
                font-size: 11px;
            }}
            .heat-legend-group {{
                justify-content: center;
                width: 100%;
            }}

            .chart-wrapper {{
                height: 200px;
            }}
        }}

        @media (max-width: 580px) {{
            .stats-6-grid {{
                grid-template-columns: repeat(2, 1fr);
                gap: 8px;
            }}
        }}

        @media (max-width: 440px) {{
            .user-pill span {{
                display: none;
            }}
            .user-pill {{
                padding: 4px 6px;
                max-width: none;
            }}
            .brand-name {{
                font-size: 14px;
            }}
        }}
    </style>
</head>
<body data-theme="light">
    <div id="tooltip"></div>
    <div class="container">

        <!-- Top Navigation -->
        <header class="navbar">
            <div class="brand-group">
                <svg style="width:20px;height:20px;flex-shrink:0;" viewBox="0 0 24 24">
                    <defs>
                        <linearGradient id="geminiSparkGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stop-color="#2563eb"/>
                            <stop offset="100%" stop-color="#ec4899"/>
                        </linearGradient>
                    </defs>
                    <path d="M12 2C12 7.5 7.5 12 2 12C7.5 12 12 16.5 12 22C12 16.5 16.5 12 22 12C16.5 12 12 7.5 12 2Z" fill="url(#geminiSparkGrad)"/>
                </svg>
                <div class="brand-name">Antigravity Token</div>
            </div>
            <div class="nav-tools">
                <button class="icon-btn" id="pinToggle" title="固定窗口 (点击后失焦不关闭)">
                    <svg id="pinIcon" class="svg-icon" viewBox="0 0 24 24"><line x1="12" y1="17" x2="12" y2="22"></line><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a1 1 0 0 0 0-2H8a1 1 0 0 0 0 2h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"></path></svg>
                </button>
                <button class="icon-btn" id="themeToggle" title="切换暗黑/明亮主题">
                    <svg id="themeIcon" class="svg-icon" viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
                </button>
                <button class="icon-btn" onclick="location.reload()" title="刷新数据">
                    <svg class="svg-icon" viewBox="0 0 24 24"><path d="M23 4v6h-6"></path><path d="M1 20v-6h6"></path><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
                </button>
            </div>
        </header>

        <!-- User Profile Hero (Codex Style) -->
        <div class="profile-section">
            <div class="avatar-wrap">
                {avatar_html}
            </div>
            <div class="profile-name">{profile['name']}</div>
            <div class="profile-handle" title="{profile['email']}">{profile['handle']}</div>
        </div>

        <!-- Codex 5-Metrics Hero Bar -->
        <section class="codex-bar">
            <div class="codex-col">
                <div class="codex-num">{format_tokens(grand_total_tokens)}</div>
                <div class="codex-label">累计 Token 数</div>
            </div>
            <div class="codex-col">
                <div class="codex-num">{format_tokens(today_tokens)}</div>
                <div class="codex-label">今日实际消耗</div>
            </div>
            <div class="codex-col">
                <div class="codex-num">{format_tokens(peak_val)}</div>
                <div class="codex-label">单日使用峰值 <span style="font-size:10px;opacity:0.75;">({peak_date[5:]})</span></div>
            </div>
            <div class="codex-col">
                <div class="codex-num">{active_days_count} 天</div>
                <div class="codex-label">活跃使用天数</div>
            </div>
            <div class="codex-col">
                <div class="codex-num">{total['turns']:,} 轮</div>
                <div class="codex-label">累计交互轮次</div>
            </div>
        </section>

        <!-- Codex Token Activity Heatmap -->
        <section class="card-container">
            <div class="section-header">
                <div class="section-title">
                    <svg class="svg-icon" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                    Token 活动
                </div>
                <div class="seg-control" id="activityControl">
                    <button class="seg-btn active" data-mode="daily">每天</button>
                    <button class="seg-btn" data-mode="weekly">每周</button>
                    <button class="seg-btn" data-mode="total">累计总量</button>
                </div>
            </div>

            <div class="activity-full-wrapper">
                <!-- 1. Daily Heatmap View -->
                <div id="heatmapPane">
                    <!-- Desktop 12 Months -->
                    <div class="month-labels-row desktop-only">
                        <span>11月</span>
                        <span>12月</span>
                        <span>1月</span>
                        <span>2月</span>
                        <span>3月</span>
                        <span>4月</span>
                        <span>5月</span>
                        <span>6月</span>
                        <span>7月</span>
                        <span>8月</span>
                        <span>9月</span>
                        <span>10月</span>
                    </div>

                    <!-- Mobile/Compact 6 Months -->
                    <div class="month-labels-row mobile-only">
                        <span>5月</span>
                        <span>6月</span>
                        <span>7月</span>
                        <span>8月</span>
                        <span>9月</span>
                        <span>10月</span>
                    </div>

                    <!-- Responsive Grid -->
                    <div class="heatmap-grid-scroll" id="heatmapGridContainer"></div>

                    <!-- Bottom Bar with Audit Info & Legend -->
                    <div class="activity-bottom-bar">
                        <div class="activity-audit-tags">
                            <div class="audit-tag-item">
                                <span>日均消耗:</span>
                                <span class="audit-tag-val">{format_tokens(avg_per_active_day)}</span>
                            </div>
                            <div class="audit-tag-item">
                                <span>单日最高:</span>
                                <span class="audit-tag-val">{format_tokens(peak_val)}</span>
                            </div>
                            <div class="audit-tag-item">
                                <span>连续活跃:</span>
                                <span class="audit-tag-val">{active_days_count} 天</span>
                            </div>
                        </div>

                        <div class="heat-legend-group">
                            <span>少</span>
                            <div class="legend-squares">
                                <div class="legend-sq" style="background: var(--heat-empty);"></div>
                                <div class="legend-sq" style="background: #93c5fd;"></div>
                                <div class="legend-sq" style="background: #60a5fa;"></div>
                                <div class="legend-sq" style="background: #2563eb;"></div>
                                <div class="legend-sq" style="background: #1e3a8a;"></div>
                            </div>
                            <span>多</span>
                        </div>
                    </div>
                </div>

                <!-- 2. Weekly / Total Chart Pane (Shows Upward Bar/Line Animation Directly) -->
                <div id="altChartPane">
                    <canvas id="altActivityChart"></canvas>
                </div>
            </div>
        </section>

        <!-- Token 消费统计 (Centered Section Header & Cards) -->
        <div class="section-header" style="justify-content: center; margin-bottom: 12px;">
            <div class="section-title">
                <svg class="svg-icon" viewBox="0 0 24 24"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
                Token 消费统计
            </div>
        </div>

        <section class="stats-6-grid">
            <div class="stat-card-box">
                <div class="stat-card-head">
                    <svg class="svg-icon" viewBox="0 0 24 24"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
                    <span>总 Token 消费</span>
                </div>
                <div class="stat-card-num">{grand_total_tokens:,}</div>
                <div class="stat-card-sub">历史有效计费总量</div>
            </div>

            <div class="stat-card-box">
                <div class="stat-card-head">
                    <svg class="svg-icon" viewBox="0 0 24 24"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>
                    <span>输入 Token (Prompt)</span>
                </div>
                <div class="stat-card-num">{total['input']:,}</div>
                <div class="stat-card-sub">提示词与上下文输入</div>
            </div>

            <div class="stat-card-box">
                <div class="stat-card-head">
                    <svg class="svg-icon" viewBox="0 0 24 24"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"></polyline><polyline points="17 18 23 18 23 12"></polyline></svg>
                    <span>输出 Token (Gen)</span>
                </div>
                <div class="stat-card-num">{total['output']:,}</div>
                <div class="stat-card-sub">思考推理与回答生成</div>
            </div>

            <div class="stat-card-box">
                <div class="stat-card-head">
                    <svg class="svg-icon" viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>
                    <span>缓存读取 (Cache)</span>
                </div>
                <div class="stat-card-num">{format_tokens(total['cache'])}</div>
                <div class="stat-card-sub">{total['cache']:,} Tokens 命中</div>
            </div>

            <div class="stat-card-box">
                <div class="stat-card-head">
                    <svg class="svg-icon" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
                    <span>总会话轮次 (Turns)</span>
                </div>
                <div class="stat-card-num">{total['turns']:,} 轮</div>
                <div class="stat-card-sub">多会话累计执行</div>
            </div>

            <div class="stat-card-box">
                <div class="stat-card-head">
                    <svg class="svg-icon" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg>
                    <span>使用模型</span>
                </div>
                <div class="stat-card-num" style="font-size:17px;padding-top:2px;">Gemini / Claude</div>
                <div class="stat-card-sub">多模型自动调度</div>
            </div>
        </section>

        <!-- Trend Chart Section -->
        <section class="card-container">
            <div class="section-header">
                <div class="section-title">
                    <svg class="svg-icon" viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
                    Token 使用趋势
                </div>
                <div class="seg-control" id="trendControl">
                    <button class="seg-btn active" data-mode="daily_bar">日走势</button>
                    <button class="seg-btn" data-mode="cumulative_line">累计总计</button>
                </div>
            </div>
            <div class="chart-wrapper">
                <canvas id="trendChart"></canvas>
            </div>
        </section>

        <!-- Table Section -->
        <section class="card-container" style="padding:0; overflow:hidden;">
            <div style="padding: 12px 16px; border-bottom: 1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center;">
                <div class="section-title">
                    <svg class="svg-icon" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                    每日消费审计明细
                </div>
                <span class="text-muted" style="font-size:11.5px;">共 {len(dates)} 天记录</span>
            </div>
            <div style="overflow-x:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>日期</th>
                            <th>交互轮次</th>
                            <th>输入 Tokens</th>
                            <th>输出 Tokens</th>
                            <th>缓存读取</th>
                            <th>当日总计 (Tokens)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
        </section>

    </div>

    <script>
        // Theme Toggle
        const themeBtn = document.getElementById('themeToggle');
        const themeIcon = document.getElementById('themeIcon');
        let currentTheme = localStorage.getItem('theme') || 'light';
        document.body.setAttribute('data-theme', currentTheme);
        renderThemeIcon(currentTheme);

        themeBtn.addEventListener('click', () => {{
            currentTheme = currentTheme === 'light' ? 'dark' : 'light';
            document.body.setAttribute('data-theme', currentTheme);
            localStorage.setItem('theme', currentTheme);
            renderThemeIcon(currentTheme);
            updateAllCharts();
        }});

        function renderThemeIcon(theme) {{
            if (theme === 'light') {{
                themeIcon.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>';
            }} else {{
                themeIcon.innerHTML = '<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>';
            }}
        }}

        // Render Heatmap with Diagonal Top-Left to Bottom-Right Wave Ripple Animation
        const weeksData = {weeks_json};
        const gridContainer = document.getElementById('heatmapGridContainer');
        const tooltip = document.getElementById('tooltip');

        function triggerHeatmapAnimation() {{
            gridContainer.innerHTML = '';
            weeksData.forEach((week, colIdx) => {{
                const colEl = document.createElement('div');
                colEl.className = 'heatmap-col';

                week.forEach((item, rowIdx) => {{
                    const cell = document.createElement('div');
                    cell.className = 'heat-cell animated';

                    // Color tiers
                    const t = item.tokens;
                    if (t > 3000000) cell.style.backgroundColor = '#1e3a8a';
                    else if (t > 1500000) cell.style.backgroundColor = '#2563eb';
                    else if (t > 500000) cell.style.backgroundColor = '#60a5fa';
                    else if (t > 0) cell.style.backgroundColor = '#93c5fd';

                    // Diagonal Staggered Ripple Delay from Top-Left to Bottom-Right: (col + row) * 10ms
                    const delayMs = (colIdx + rowIdx) * 10;
                    cell.style.animationDelay = delayMs + 'ms';

                    function updateTooltipPos(ev) {{
                        const tipW = tooltip.offsetWidth || 185;
                        const tipH = tooltip.offsetHeight || 110;
                        const clientW = document.documentElement.clientWidth || window.innerWidth;

                        // Flip to left of cursor if near the right edge!
                        let x = ev.clientX + 12;
                        if (x + tipW > clientW - 12) {{
                            x = ev.clientX - tipW - 12;
                        }}
                        if (x < 10) x = 10;

                        // Vertical position: flip downward if near top edge
                        let y = ev.clientY - tipH - 8;
                        if (y < 10) {{
                            y = ev.clientY + 18;
                        }}

                        tooltip.style.left = x + 'px';
                        tooltip.style.top = y + 'px';
                    }}

                    cell.addEventListener('mouseenter', (e) => {{
                        tooltip.style.display = 'block';
                        let content = `<div style="font-weight:650;font-size:12px;margin-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.15);padding-bottom:3px;">${{item.date}}</div>`;
                        if (item.tokens > 0) {{
                            content += `<div style="display:flex;justify-content:space-between;gap:14px;font-weight:600;margin-bottom:4px;color:#38bdf8;"><span>总消耗:</span><span>${{item.tokens.toLocaleString()}}</span></div>`;
                            content += `<div style="display:flex;justify-content:space-between;gap:14px;color:#94a3b8;font-size:11px;"><span>未命中输入:</span><span style="color:#60a5fa;">${{(item.input || 0).toLocaleString()}}</span></div>`;
                            content += `<div style="display:flex;justify-content:space-between;gap:14px;color:#94a3b8;font-size:11px;"><span>命中缓存:</span><span style="color:#a5b4fc;">${{(item.cache || 0).toLocaleString()}}</span></div>`;
                            content += `<div style="display:flex;justify-content:space-between;gap:14px;color:#94a3b8;font-size:11px;"><span>模型输出:</span><span style="color:#f472b6;">${{(item.output || 0).toLocaleString()}}</span></div>`;
                            content += `<div style="display:flex;justify-content:space-between;gap:14px;color:#94a3b8;font-size:11px;margin-top:4px;border-top:1px dashed rgba(255,255,255,0.1);padding-top:3px;"><span>交互轮次:</span><span style="color:#f1f5f9;">${{item.turns}} 轮</span></div>`;
                        }} else {{
                            content += `<div style="color:#94a3b8;font-size:11px;">无使用记录</div>`;
                        }}
                        tooltip.innerHTML = content;
                        updateTooltipPos(e);
                    }});

                    cell.addEventListener('mousemove', (e) => {{
                        updateTooltipPos(e);
                    }});

                    cell.addEventListener('mouseleave', () => {{
                        tooltip.style.display = 'none';
                    }});

                    colEl.appendChild(cell);
                }});

                gridContainer.appendChild(colEl);
            }});
        }}

        triggerHeatmapAnimation();

        // Activity Segments: Instant container display to let Chart.js play its bar/line rising animations!
        const activityBtns = document.querySelectorAll('#activityControl .seg-btn');
        const heatmapPane = document.getElementById('heatmapPane');
        const altChartPane = document.getElementById('altChartPane');
        let altChart = null;
        let currentActivityMode = 'daily';

        activityBtns.forEach(btn => {{
            btn.addEventListener('click', () => {{
                const targetMode = btn.getAttribute('data-mode');
                if (targetMode === currentActivityMode) return;

                activityBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentActivityMode = targetMode;

                if (targetMode === 'daily') {{
                    altChartPane.style.display = 'none';
                    heatmapPane.style.display = 'block';
                    triggerHeatmapAnimation();
                }} else {{
                    heatmapPane.style.display = 'none';
                    altChartPane.style.display = 'block';
                    // Render chart immediately so bars & lines rise up dynamically from bottom!
                    renderAltChart(targetMode);
                }}
            }});
        }});

        function renderAltChart(mode) {{
            const isDark = document.body.getAttribute('data-theme') === 'dark';
            const gridColor = isDark ? '#1e293b' : '#f1f5f9';
            const tickColor = isDark ? '#94a3b8' : '#64748b';
            const ctxAlt = document.getElementById('altActivityChart').getContext('2d');

            if (altChart) altChart.destroy();

            const chartData = mode === 'weekly' ? {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(week_labels)},
                    datasets: [{{
                        label: '周度 Token 汇总',
                        data: {json.dumps(week_totals)},
                        backgroundColor: '#2563eb',
                        borderRadius: 4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{
                        mode: 'index',
                        intersect: false
                    }},
                    animation: {{
                        duration: 650,
                        easing: 'easeOutQuart'
                    }},
                    scales: {{
                        x: {{ grid: {{ display: false }}, ticks: {{ color: tickColor, font: {{ size: 10 }} }} }},
                        y: {{ grid: {{ color: gridColor }}, ticks: {{ color: tickColor, font: {{ size: 10 }} }} }}
                    }},
                    plugins: {{ legend: {{ display: false }} }}
                }}
            }} : {{
                type: 'line',
                data: {{
                    labels: {json.dumps(chart_dates)},
                    datasets: [{{
                        label: '历史累计总量',
                        data: {json.dumps(chart_cumulative)},
                        borderColor: '#2563eb',
                        backgroundColor: 'rgba(37, 99, 235, 0.08)',
                        fill: true,
                        tension: 0.3,
                        borderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 7,
                        pointHitRadius: 25,
                        pointHoverBackgroundColor: '#2563eb',
                        pointHoverBorderColor: '#ffffff',
                        pointHoverBorderWidth: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{
                        mode: 'index',
                        intersect: false
                    }},
                    animation: {{
                        duration: 650,
                        easing: 'easeOutQuart'
                    }},
                    scales: {{
                        x: {{ grid: {{ display: false }}, ticks: {{ color: tickColor, font: {{ size: 10 }} }} }},
                        y: {{ grid: {{ color: gridColor }}, ticks: {{ color: tickColor, font: {{ size: 10 }} }} }}
                    }},
                    plugins: {{ legend: {{ display: false }} }}
                }}
            }};

            altChart = new Chart(ctxAlt, chartData);
        }}

        // Trend Chart with Smooth Transitions
        const trendBtns = document.querySelectorAll('#trendControl .seg-btn');
        const ctxTrend = document.getElementById('trendChart').getContext('2d');
        let trendChart = null;
        let trendMode = 'daily_bar';

        trendBtns.forEach(btn => {{
            btn.addEventListener('click', () => {{
                trendBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                trendMode = btn.getAttribute('data-mode');
                renderTrendChart();
            }});
        }});

        function renderTrendChart() {{
            const isDark = document.body.getAttribute('data-theme') === 'dark';
            const gridColor = isDark ? '#1e293b' : '#f1f5f9';
            const tickColor = isDark ? '#94a3b8' : '#64748b';

            if (trendChart) trendChart.destroy();

            if (trendMode === 'daily_bar') {{
                trendChart = new Chart(ctxTrend, {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps(chart_dates)},
                        datasets: [
                            {{
                                label: '未命中输入 (Input)',
                                data: {json.dumps(chart_inputs)},
                                backgroundColor: '#3b82f6',
                                borderRadius: 4
                            }},
                            {{
                                label: '命中缓存 (Cache)',
                                data: {json.dumps(chart_caches)},
                                backgroundColor: '#6366f1',
                                borderRadius: 4
                            }},
                            {{
                                label: '模型输出 (Output)',
                                data: {json.dumps(chart_outputs)},
                                backgroundColor: '#ec4899',
                                borderRadius: 4
                            }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {{
                            mode: 'index',
                            intersect: false
                        }},
                        animation: {{
                            duration: 600,
                            easing: 'easeOutQuart'
                        }},
                        scales: {{
                            x: {{ stacked: true, grid: {{ color: gridColor }}, ticks: {{ color: tickColor }} }},
                            y: {{
                                stacked: true,
                                grid: {{ color: gridColor }},
                                ticks: {{
                                    color: tickColor,
                                    callback: function(v) {{
                                        if (v >= 1000000) return (v / 1000000).toFixed(1) + 'M';
                                        if (v >= 1000) return (v / 1000).toFixed(0) + 'K';
                                        return v;
                                    }}
                                }}
                            }}
                        }},
                        plugins: {{
                            legend: {{ labels: {{ color: tickColor, font: {{ size: 11.5, weight: '500' }} }} }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(c) {{ return c.dataset.label + ': ' + c.parsed.y.toLocaleString(); }}
                                }}
                            }}
                        }}
                    }}
                }});
            }} else {{
                trendChart = new Chart(ctxTrend, {{
                    type: 'line',
                    data: {{
                        labels: {json.dumps(chart_dates)},
                        datasets: [{{
                            label: '全量累计消耗曲线',
                            data: {json.dumps(chart_cumulative)},
                            borderColor: '#2563eb',
                            backgroundColor: isDark ? 'rgba(56, 189, 248, 0.1)' : 'rgba(37, 99, 235, 0.08)',
                            fill: true,
                            tension: 0.35,
                            borderWidth: 2.5,
                            pointRadius: 4,
                            pointHoverRadius: 7,
                            pointHitRadius: 25,
                            pointBackgroundColor: '#2563eb',
                            pointHoverBackgroundColor: '#2563eb',
                            pointHoverBorderColor: '#ffffff',
                            pointHoverBorderWidth: 2
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {{
                            mode: 'index',
                            intersect: false
                        }},
                        animation: {{
                            duration: 600,
                            easing: 'easeOutQuart'
                        }},
                        scales: {{
                            x: {{ grid: {{ color: gridColor }}, ticks: {{ color: tickColor }} }},
                            y: {{
                                grid: {{ color: gridColor }},
                                ticks: {{
                                    color: tickColor,
                                    callback: function(v) {{
                                        if (v >= 1000000) return (v / 1000000).toFixed(1) + 'M';
                                        if (v >= 1000) return (v / 1000).toFixed(0) + 'K';
                                        return v;
                                    }}
                                }}
                            }}
                        }},
                        plugins: {{
                            legend: {{ labels: {{ color: tickColor, font: {{ size: 11.5, weight: '500' }} }} }}
                        }}
                    }}
                }});
            }}
        }}

        function updateAllCharts() {{
            renderTrendChart();
            if (currentActivityMode !== 'daily') {{
                renderAltChart(currentActivityMode);
            }}
        }}

        renderTrendChart();

        // Pin Window Toggle (Keep open on blur vs auto-close)
        const pinBtn = document.getElementById('pinToggle');
        let isPinned = localStorage.getItem('windowPinned') === 'true';

        function updatePinDisplay() {{
            if (isPinned) {{
                pinBtn.classList.add('active');
                pinBtn.title = "已固定窗口 (点击恢复点击外部自动关闭)";
            }} else {{
                pinBtn.classList.remove('active');
                pinBtn.title = "固定窗口 (点击后失焦不关闭)";
            }}
        }}
        updatePinDisplay();

        pinBtn.addEventListener('click', () => {{
            isPinned = !isPinned;
            localStorage.setItem('windowPinned', isPinned ? 'true' : 'false');
            updatePinDisplay();
        }});

        // Close window when clicking outside (on blur)
        let closeOnBlurArmed = false;
        setTimeout(() => {{
            closeOnBlurArmed = true;
        }}, 600);

        window.addEventListener('blur', () => {{
            if (!isPinned && closeOnBlurArmed) {{
                try {{
                    window.close();
                }} catch (e) {{}}
            }}
        }});
    </script>
</body>
</html>
"""
    with open(DASHBOARD_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    return DASHBOARD_HTML

if __name__ == "__main__":
    daily, total = analyze_usage()
    out = build_codex_style_html(daily, total)
    print("SUCCESS:", out)
