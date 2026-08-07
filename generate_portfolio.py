import csv
import json
import os
import webbrowser
from datetime import datetime
from pathlib import Path

DOWNLOAD = Path.home() / "Downloads"
CSV_PATTERN = "portefeuille-5MK5V-ALL*.csv"

def find_csv():
    files = sorted(DOWNLOAD.glob(CSV_PATTERN), key=os.path.getmtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No CSV matching '{CSV_PATTERN}' found in {DOWNLOAD}")
    return files[0]

def parse_number(s):
    s = s.strip().replace(",", ".").replace("\u00a0", "")
    if s in ("", "N/D"):
        return None
    return float(s)

def parse_csv(path):
    with open(path, newline="", encoding="latin-1") as f:
        reader = csv.reader(f, delimiter=";")
        rows = list(reader)

    data = {"CAD": [], "USD": []}
    current_section = None

    for row in rows:
        if not row or not row[0].strip():
            continue
        first = row[0].strip()
        if first == "ACTIONS CAD":
            current_section = "CAD"
            continue
        elif first == "ACTIONS USD":
            current_section = "USD"
            continue
        elif first == "sep=;" or first.startswith("Compte"):
            continue

        if current_section and len(row) >= 15:
            data[current_section].append({
                "symbol": row[1].strip() if len(row) > 1 else "",
                "nom": row[2].strip() if len(row) > 2 else "",
                "qty": parse_number(row[3]) if len(row) > 3 else None,
                "avg_cost": parse_number(row[4]) if len(row) > 4 else None,
                "total_cost": parse_number(row[5]) if len(row) > 5 else None,
                "curr_price": parse_number(row[7]) if len(row) > 7 else None,
                "day_change_d": parse_number(row[8]) if len(row) > 8 else None,
                "day_change_p": parse_number(row[9]) if len(row) > 9 else None,
                "market_value": parse_number(row[11]) if len(row) > 11 else None,
                "unrealized_pnl": parse_number(row[13]) if len(row) > 13 else None,
                "unrealized_pnl_p": parse_number(row[14]) if len(row) > 14 else None,
            })
    return data

def enrich(data, csv_path=None):
    grand_cost = sum(
        sum(i["total_cost"] for i in items if i["total_cost"] is not None)
        for items in data.values()
    )
    grand_mv = sum(
        sum(i["market_value"] for i in items if i["market_value"] is not None)
        for items in data.values()
    )
    grand_pnl = sum(
        sum(i["unrealized_pnl"] for i in items if i["unrealized_pnl"] is not None)
        for items in data.values()
    )
    for items in data.values():
        for i in items:
            tc = i["total_cost"]
            i["pct_portfolio"] = round(tc / grand_cost * 100, 1) if tc and grand_cost else None
    data["meta"] = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": str(csv_path or find_csv()),
        "grand_total_cost": grand_cost,
        "grand_total_mv": grand_mv,
        "grand_total_pnl": grand_pnl,
    }
    return data

def generate_html(data):
    saved_budget = {"budget": 1000, "qtys": {}}
    saved_path = Path(__file__).parent / "portfolio-budget.json"
    if saved_path.exists():
        try:
            with open(saved_path) as f:
                saved_budget = json.load(f)
        except Exception:
            pass
    saved_json = json.dumps(saved_budget)
    data_json = json.dumps(data)
    return HTML_TEMPLATE.replace("__SAVED_JSON__", saved_json).replace("__DATA_JSON__", data_json)

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portfolio Dashboard</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0f172a;
    color: #e2e8f0;
    padding: 2rem;
}
h1 { font-size: 1.8rem; margin-bottom: 0.25rem; }
.subtitle { color: #94a3b8; margin-bottom: 2rem; font-size: 0.9rem; }
#loading { color: #64748b; text-align: center; padding: 4rem; font-size: 1.1rem; }
.overall {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;
    margin-bottom: 2rem;
}
.card {
    background: #1e293b; border-radius: 12px; padding: 1.25rem;
    border: 1px solid #334155;
}
.card .label { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; }
.card .value { font-size: 1.5rem; font-weight: 700; margin-top: 0.25rem; }
.card.positive .value { color: #22c55e; }
.card.negative .value { color: #ef4444; }
.section { margin-bottom: 2.5rem; }
.section h2 { font-size: 1.25rem; margin-bottom: 1rem; color: #f1f5f9; }
.summary-row {
    display: flex; gap: 1rem; margin-bottom: 1rem;
}
.summary-card {
    background: #1e293b; border-radius: 8px; padding: 0.75rem 1rem;
    border: 1px solid #334155; flex: 1;
}
.summary-card .label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; }
.summary-card .value { font-size: 1.1rem; font-weight: 600; margin-top: 0.15rem; }
.summary-card.positive .value { color: #22c55e; }
.summary-card.negative .value { color: #ef4444; }
table {
    width: 100%; border-collapse: collapse;
    background: #1e293b; border-radius: 12px; overflow: hidden;
    border: 1px solid #334155;
}
th {
    background: #0f172a; padding: 0.75rem 0.5rem;
    text-align: right; font-size: 0.75rem; text-transform: uppercase;
    letter-spacing: 0.05em; color: #64748b; border-bottom: 1px solid #334155;
    white-space: nowrap; cursor: pointer; user-select: none;
}
th:first-child { text-align: left; padding-left: 1rem; }
th:hover { color: #f1f5f9; }
th .sort { margin-left: 4px; opacity: 0.4; }
th.sort-asc .sort, th.sort-desc .sort { opacity: 1; }
td {
    padding: 0.6rem 0.5rem; text-align: right;
    font-size: 0.85rem; border-bottom: 1px solid #1e293b;
    font-variant-numeric: tabular-nums;
}
td:first-child { text-align: left; padding-left: 1rem; font-weight: 600; color: #f1f5f9; }
td:nth-child(2) { text-align: left; color: #94a3b8; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
tr:hover { background: #334155; }
tr.row-focused { background: #1e3a5f; outline: 1px solid #6366f1; }
tr:last-child td { border-bottom: none; }
input[type="number"] {
    padding: 4px 6px; border-radius: 6px;
    border: 1px solid #334155; background: #0f172a; color: #e2e8f0;
    text-align: right; font-size: 0.85rem;
}
input[type="number"]:focus { outline: none; border-color: #6366f1; }
.summary-card input.budget-input {
    width: 120px; padding: 6px 8px; font-size: 1rem; font-weight: 700;
    background: transparent; border: 1px solid #475569;
}
.budget-cost { font-variant-numeric: tabular-nums; }
.budget-remaining { font-size: 0.7rem; color: #94a3b8; margin-top: 2px; }
.budget-reset {
    background: none; border: none; color: #64748b; cursor: pointer;
    font-size: 1rem; padding: 0 2px; margin-left: 4px;
    vertical-align: middle; line-height: 1;
}
.budget-reset:hover { color: #f1f5f9; }
.budget-card { display: flex; flex-wrap: wrap; align-items: center; position: relative; }
.budget-card .label { width: auto; }
.budget-card .budget-reset {
    position: absolute; right: 0.75rem; top: 0.75rem;
    background: #ef4444; border: none; color: #fff; cursor: pointer;
    font-size: 1.1rem; padding: 2px 6px; border-radius: 4px;
}
.budget-card .budget-reset:hover { background: #dc2626; }
.budget-card .value { width: 100%; }
.budget-card .budget-remaining { width: 100%; }
button {
    padding: 8px 16px; border-radius: 8px; border: none;
    font-size: 0.85rem; font-weight: 600; cursor: pointer;
}
#budget-save { background: #6366f1; color: #fff; }
#budget-save:hover { background: #4f46e5; }
#budget-export { background: #1e293b; color: #e2e8f0; border: 1px solid #334155; }
#budget-export:hover { background: #334155; }
</style>
</head>
<body>
<h1>Portfolio Dashboard</h1>
<div class="subtitle" id="subtitle">Loading...</div>
<div id="loading">Loading portfolio data...</div>

<div id="dashboard" style="display:none">
<div class="overall" id="overall-cards"></div>

<div style="display:flex; gap:1rem; margin-bottom:2rem;">
    <button id="budget-save">Save Budget</button>
    <button id="budget-export">Export JSON</button>
</div>

<div id="sections"></div>
</div>

<script>
const DATA = __DATA_JSON__;
const SAVED = __SAVED_JSON__;
const STORAGE_KEY = "portfolio-budget-data";

function loadSaved() {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) return JSON.parse(stored);
    } catch(e) {}
    return SAVED;
}

let savedData = loadSaved();

if (savedData._generated && savedData._generated !== DATA.meta.generated) {
    savedData = { budget: 0, qtys: {}, _generated: DATA.meta.generated };
    persistData();
}
if (!savedData._generated) {
    savedData._generated = DATA.meta.generated;
    persistData();
}

function fmt(n, suffix) {
    if (n == null) return "N/D";
    return Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + (suffix || "$");
}

function cssColor(val) {
    if (val == null) return "";
    return val >= 0 ? "color: #22c55e" : "color: #ef4444";
}

function persistData() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(savedData)); } catch(e) {}
}

function renderDashboard(data) {
    const meta = data.meta;
    const sections = ["CAD", "USD"];
    const pnlCls = meta.grand_total_pnl >= 0 ? "positive" : "negative";

    document.getElementById("subtitle").textContent = "Generated " + meta.generated + " -- Source: " + meta.source;

    document.getElementById("overall-cards").innerHTML =
        '<div class="card"><div class="label">Total Market Value</div><div class="value">' + fmt(meta.grand_total_mv) + '</div></div>' +
        '<div class="card"><div class="label">Total Cost</div><div class="value">' + fmt(meta.grand_total_cost) + '</div></div>' +
        '<div class="card ' + pnlCls + '"><div class="label">Total Unrealized P&L</div><div class="value">' + fmt(meta.grand_total_pnl) + '</div></div>';

    let sectionsHtml = "";
    for (const key of sections) {
        const items = data[key];
        if (!items || !items.length) continue;

        const totalMv = items.reduce((s, i) => s + (i.market_value || 0), 0);
        const totalCost = items.reduce((s, i) => s + (i.total_cost || 0), 0);
        const totalPnl = items.reduce((s, i) => s + (i.unrealized_pnl || 0), 0);
        const pnlClass = totalPnl >= 0 ? "positive" : "negative";

        let rows = "";
        for (const i of items) {
            rows += '<tr>' +
                '<td>' + i.symbol + '</td>' +
                '<td>' + i.nom + '</td>' +
                '<td>' + i.qty + '</td>' +
                '<td>' + fmt(i.avg_cost) + '</td>' +
                '<td>' + fmt(i.total_cost) + '</td>' +
                '<td>' + fmt(i.curr_price) + '</td>' +
                '<td style="' + cssColor(i.day_change_d) + '">' + fmt(i.day_change_d) + '</td>' +
                '<td style="' + cssColor(i.day_change_p) + '">' + (i.day_change_p != null ? fmt(i.day_change_p, "%") : "N/D") + '</td>' +
                '<td>' + fmt(i.market_value) + '</td>' +
                '<td style="' + cssColor(i.unrealized_pnl) + '">' + fmt(i.unrealized_pnl) + '</td>' +
                '<td style="' + cssColor(i.unrealized_pnl_p) + '">' + (i.unrealized_pnl_p != null ? fmt(i.unrealized_pnl_p, "%") : "N/D") + '</td>' +
                '<td class="pct-portfolio" data-cost="' + (i.total_cost || 0) + '" data-grand="' + meta.grand_total_cost + '">' + (i.pct_portfolio != null ? i.pct_portfolio + "%" : "-") + '</td>' +
                '<td><input class="budget-qty" type="number" min="0" step="1" value="0" data-symbol="' + i.symbol + '" data-price="' + (i.curr_price || 0) + '"></td>' +
                '<td class="budget-cost">0.00$</td>' +
                '<td class="budget-canbuy">-</td>' +
                '</tr>';
        }

        sectionsHtml +=
            '<div class="section">' +
            '<h2>' + key + ' Stocks</h2>' +
            '<div class="summary-row">' +
            '<div class="summary-card"><span class="label">Market Value</span><span class="value">' + fmt(totalMv) + '</span></div>' +
            '<div class="summary-card"><span class="label">Total Cost</span><span class="value">' + fmt(totalCost) + '</span></div>' +
            '<div class="summary-card ' + pnlClass + '"><span class="label">Unrealized P&L</span><span class="value">' + fmt(totalPnl) + '</span></div>' +
            '<div class="summary-card budget-card"><span class="label">Budget</span><button class="budget-reset" title="Reset budget &amp; qty">&#x21ba;</button><span class="value"><input class="budget-input" type="number" min="0" step="100" value="' + (savedData.budget || 0) + '" placeholder="0"></span><div class="budget-remaining">Remaining: ' + Number(savedData.budget || 0).toLocaleString() + '$</div></div>' +
            '</div>' +
            '<table>' +
            '<thead><tr>' +
            '<th data-type="text">Symbol<span class="sort"></span></th>' +
            '<th data-type="text">Name<span class="sort"></span></th>' +
            '<th data-type="num">Qty<span class="sort"></span></th>' +
            '<th data-type="num">Avg Cost<span class="sort"></span></th>' +
            '<th data-type="num">Total Cost<span class="sort"></span></th>' +
            '<th data-type="num">Price<span class="sort"></span></th>' +
            '<th data-type="num">Day Chg $<span class="sort"></span></th>' +
            '<th data-type="num">Day Chg %<span class="sort"></span></th>' +
            '<th data-type="num">Market Value<span class="sort"></span></th>' +
            '<th data-type="num">Unrealized P&L $<span class="sort"></span></th>' +
            '<th data-type="num">Unrealized P&L %<span class="sort"></span></th>' +
            '<th data-type="num">% Portfolio<span class="sort"></span></th>' +
            '<th>Buy Qty</th>' +
            '<th data-type="num">Cost<span class="sort"></span></th>' +
            '<th data-type="num">Can Buy<span class="sort"></span></th>' +
            '</tr></thead>' +
            '<tbody>' + rows + '</tbody>' +
            '</table>' +
            '</div>';
    }

    document.getElementById("sections").innerHTML = sectionsHtml;

    document.querySelectorAll(".budget-qty").forEach(inp => {
        const sym = inp.dataset.symbol;
        if (savedData.qtys && savedData.qtys[sym]) inp.value = savedData.qtys[sym];
    });

    recalcBudget();
    wireEvents();

    document.querySelectorAll(".section th[data-type='num']").forEach(th => {
        if (th.textContent.trim().startsWith("% Portfolio")) {
            th.click();
        }
    });

    document.getElementById("loading").style.display = "none";
    document.getElementById("dashboard").style.display = "block";
}

function recalcBudget() {
    const budget = parseFloat(document.querySelector(".budget-input").value) || 0;
    let total = 0;
    document.querySelectorAll(".budget-qty").forEach(inp => {
        const qty = parseFloat(inp.value) || 0;
        const price = parseFloat(inp.dataset.price) || 0;
        const cost = qty * price;
        total += cost;
        const row = inp.closest("tr");
        if (row) row.querySelector(".budget-cost").textContent = cost.toFixed(2) + "$";
    });
    const remaining = budget - total;
    document.querySelectorAll(".budget-remaining").forEach(el => el.textContent = "Remaining: " + remaining.toFixed(2) + "$");
    document.querySelectorAll(".budget-qty").forEach(inp => {
        const qty = parseFloat(inp.value) || 0;
        const price = parseFloat(inp.dataset.price) || 0;
        const row = inp.closest("tr");
        if (!row) return;
        const can = (price > 0 && remaining > 0) ? Math.floor(remaining / price) : "-";
        row.querySelector(".budget-canbuy").textContent = can;
    });
    document.querySelectorAll(".pct-portfolio").forEach(td => {
        const cost = parseFloat(td.dataset.cost) || 0;
        const grand = parseFloat(td.dataset.grand) || 0;
        const row = td.closest("tr");
        const inp = row ? row.querySelector(".budget-qty") : null;
        const buyQty = parseFloat(inp ? inp.value : 0) || 0;
        const price = parseFloat(inp ? inp.dataset.price : 0) || 0;
        const buyCost = buyQty * price;
        const cur = grand ? (cost / grand * 100) : 0;
        const newGrand = grand + total;
        const proj = newGrand ? ((cost + buyCost) / newGrand * 100) : 0;
        td.textContent = cur.toFixed(1) + "%" + (buyCost > 0 ? " (" + proj.toFixed(1) + "%)" : "");
    });
}

function wireEvents() {
    document.querySelectorAll(".budget-input").forEach(inp => inp.addEventListener("input", () => {
        const v = inp.value;
        document.querySelectorAll(".budget-input").forEach(other => other.value = v);
        savedData.budget = parseFloat(v) || 0;
        persistData();
        recalcBudget();
    }));
    document.querySelectorAll(".budget-qty").forEach(inp => inp.addEventListener("input", () => {
        const sym = inp.dataset.symbol;
        const v = parseFloat(inp.value);
        if (v) savedData.qtys[sym] = v;
        else delete savedData.qtys[sym];
        persistData();
        recalcBudget();
    }));
    document.querySelectorAll(".budget-qty").forEach(inp => {
        inp.addEventListener("focus", () => inp.closest("tr")?.classList.add("row-focused"));
        inp.addEventListener("blur", () => inp.closest("tr")?.classList.remove("row-focused"));
    });
    document.querySelectorAll(".budget-reset").forEach(btn => btn.addEventListener("click", () => {
        savedData = { budget: 0, qtys: {}, _generated: DATA.meta.generated };
        persistData();
        document.querySelectorAll(".budget-input").forEach(inp => inp.value = 0);
        document.querySelectorAll(".budget-qty").forEach(inp => inp.value = 0);
        recalcBudget();
    }));
    document.getElementById("budget-save").addEventListener("click", () => {
        const qtys = {};
        document.querySelectorAll(".budget-qty").forEach(inp => {
            const v = parseFloat(inp.value);
            if (v) qtys[inp.dataset.symbol] = v;
        });
        const data = {
            budget: parseFloat(document.querySelector(".budget-input").value) || 0,
            qtys: qtys
        };
        const blob = new Blob([JSON.stringify(data, null, 2)], {type: "application/json"});
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "portfolio-budget.json";
        a.click();
    });
    document.getElementById("budget-export").addEventListener("click", () => {
        const blob = new Blob([JSON.stringify(window._portfolioData, null, 2)], {type: "application/json"});
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "portfolio-budget.json";
        a.click();
    });

    document.querySelectorAll("table").forEach(table => {
        const headers = table.querySelectorAll("th");
        const tbody = table.querySelector("tbody");
        headers.forEach((th, col) => {
            th.addEventListener("click", () => {
                if (!th.dataset.type) return;
                const isNum = th.dataset.type === "num";
                const rows = Array.from(tbody.querySelectorAll("tr"));
                const current = th.classList.contains("sort-asc") ? "desc" : th.classList.contains("sort-desc") ? "none" : "asc";
                headers.forEach(h => h.classList.remove("sort-asc", "sort-desc"));
                if (current === "none") return;
                th.classList.add(current === "asc" ? "sort-asc" : "sort-desc");
                const m = current === "asc" ? 1 : -1;
                rows.sort((a, b) => {
                    const va = a.children[col].textContent.trim();
                    const vb = b.children[col].textContent.trim();
                    if (isNum) {
                        const na = parseFloat(va.replace(/[$,%()]/g, "")) || 0;
                        const nb = parseFloat(vb.replace(/[$,%()]/g, "")) || 0;
                        return (na - nb) * m;
                    }
                    return va.localeCompare(vb) * m;
                });
                rows.forEach(r => tbody.appendChild(r));
            });
        });
    });
}

window._portfolioData = DATA;
renderDashboard(DATA);
</script>
</body>
</html>"""

def main():
    csv_path = find_csv()

    print(f"Reading: {csv_path}")
    data = parse_csv(csv_path)
    data = enrich(data, csv_path)

    cad_count = len(data["CAD"])
    usd_count = len(data["USD"])
    print(f"Found {cad_count} CAD holdings, {usd_count} USD holdings")

    json_data = {k: v for k, v in data.items() if k != "meta"}
    json_data["meta"] = data["meta"]

    json_path = Path(__file__).parent / "portfolio.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"Written: {json_path}")

    out_csv = Path(__file__).parent / "portfolio.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Symbol", "Name", "Qty", "Avg Cost", "Total Cost", "Price",
                     "Day Chg $", "Day Chg %", "Market Value", "Unrealized P&L $",
                     "Unrealized P&L %", "% Portfolio"])
        for key in ["CAD", "USD"]:
            for i in data.get(key, []):
                w.writerow([
                    i["symbol"], i["nom"], i["qty"], i["avg_cost"], i["total_cost"],
                    i["curr_price"], i["day_change_d"], i["day_change_p"],
                    i["market_value"], i["unrealized_pnl"], i["unrealized_pnl_p"],
                    i["pct_portfolio"],
                ])
    print(f"Written: {out_csv}")

    html = generate_html(data)
    output_html = Path(__file__).parent / "portfolio.html"
    output_html.write_text(html, encoding="utf-8")
    print(f"Written: {output_html}")

    webbrowser.open(output_html.as_uri())

if __name__ == "__main__":
    main()
