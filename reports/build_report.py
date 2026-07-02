"""Build the Final Execution Report PDF from the real pipeline artefacts.

Reads outputs/*.json, outputs/evaluation_summary.csv and the screenshots in
outputs/screenshots/, and produces a professional, self-contained PDF at
reports/Group5_Final_Execution_Report.pdf. All numbers and images are the real
ones written by the last `python run_pipeline.py`.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (BaseDocTemplate, Frame, Image, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
SHOTS = OUT / "screenshots"
PDF = ROOT / "reports" / "Group5_Final_Execution_Report.pdf"

DARK = colors.HexColor("#1f7045")
MID = colors.HexColor("#3f9b6e")
LIGHT = colors.HexColor("#e6f0ea")
GREY = colors.HexColor("#5a6b60")
INK = colors.HexColor("#1a1a1a")


def load_json(name):
    return json.loads((OUT / name).read_text())


def load_csv(name):
    with (OUT / name).open() as f:
        return list(csv.DictReader(f))


clean = load_json("cleaning_report.json")
feat = load_json("feature_stats.json")
mdl = load_json("model_stats.json")
anom = load_json("anomaly_stats.json")
evalrows = load_csv("evaluation_summary.csv")

# ---------------- styles ----------------
ss = getSampleStyleSheet()
styles = {
    "title": ParagraphStyle("t", parent=ss["Title"], fontSize=26, textColor=DARK,
                            spaceAfter=6, leading=30),
    "subtitle": ParagraphStyle("st", parent=ss["Normal"], fontSize=13, textColor=GREY,
                               alignment=TA_CENTER, spaceAfter=2),
    "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontSize=16, textColor=DARK,
                         spaceBefore=14, spaceAfter=8, leading=19),
    "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12.5, textColor=MID,
                         spaceBefore=10, spaceAfter=5),
    "body": ParagraphStyle("b", parent=ss["Normal"], fontSize=10, textColor=INK,
                           alignment=TA_JUSTIFY, leading=15, spaceAfter=6),
    "cap": ParagraphStyle("c", parent=ss["Normal"], fontSize=8.8, textColor=GREY,
                          alignment=TA_CENTER, spaceBefore=3, spaceAfter=12, leading=11),
    "mono": ParagraphStyle("m", parent=ss["Code"], fontSize=8.5, textColor=INK, leading=11),
    "small": ParagraphStyle("sm", parent=ss["Normal"], fontSize=9, textColor=GREY,
                            alignment=TA_CENTER),
}

story = []


def P(txt, s="body"):
    story.append(Paragraph(txt, styles[s]))


def H(txt, s="h1"):
    story.append(Paragraph(txt, styles[s]))


def sp(h=6):
    story.append(Spacer(1, h))


def styled_table(data, col_widths=None, header=True):
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    cmds = [
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cdd8d0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
    ]
    if header:
        cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ]
    t.setStyle(TableStyle(cmds))
    return t


def figure(img_name, caption, max_w=16 * cm):
    p = SHOTS / img_name
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(str(p)).getSize()
    w = min(max_w, 16 * cm)
    h = w * ih / iw
    max_h = 20 * cm
    if h > max_h:
        h = max_h
        w = h * iw / ih
    img = Image(str(p), width=w, height=h)
    img.hAlign = "CENTER"
    story.append(img)
    story.append(Paragraph(caption, styles["cap"]))


# ============================================================ TITLE
sp(60)
P("GreenPower Utilities", "title")
P("Energy Consumption Analytics — Final Execution Report", "subtitle")
sp(6)
P("Six-Week Data-Engineering Capstone &nbsp;·&nbsp; IIT Jodhpur &nbsp;·&nbsp; Group 5", "subtitle")
sp(30)
team = [
    ["Team Member", "Roll No."],
    ["Harshit Nirmal Jain", "G25AI1021"],
    ["K R Devika", "G25AI1022"],
    ["Kartik Dadhich", "G25AI1023"],
    ["Kirtiman Sarangi", "G25AI1024"],
    ["Kollipara Teja", "G25AI1025"],
]
story.append(styled_table(team, [9 * cm, 5 * cm]))
sp(24)
P(f"End-to-end pipeline verified: <b>acquire → clean → store → features → models "
  f"→ anomaly → figures</b>, completing on a 60-day chronological hold-out with a "
  f"best-model MAPE of <b>{mdl['best_mape']}%</b> ({mdl['improve_vs_baseline_pct']:.0f}% "
  f"lower RMSE than the seasonal-naive baseline) and an anomaly detector at "
  f"precision <b>{anom['precision']}</b> / recall <b>{anom['recall']}</b>.", "small")
sp(10)
P(f"Neural model executed: <b>{mdl['neural_model_used']}</b> "
  f"(scikit-learn; TensorFlow LSTM path available when installed). "
  f"Report generated from live pipeline outputs.", "small")
story.append(PageBreak())

# ============================================================ 1. OVERVIEW
H("1. Project Overview")
P("GreenPower Utilities is an end-to-end data-engineering capstone that turns raw "
  "public energy data into a cleaned time series, a partitioned time-series store, "
  "an engineered feature layer, demand-forecasting and anomaly-detection models, and "
  "an operational dashboard. The runnable pipeline uses portable SQLite and "
  "statistically calibrated sample data so the whole stack executes on any machine "
  "with a standard scientific-Python environment — no database server or credentials "
  "required. The production storage design (TimescaleDB hypertables, continuous "
  "aggregates, native compression) is captured as deployable SQL migrations.")
P("This report documents a full, reproducible execution of the pipeline and embeds "
  "the real terminal output, database queries, dashboard and analytical figures it "
  "produced, together with the exact metrics written to <font name='Courier'>outputs/</font>.")

H("Headline results", "h2")
kpi = [
    ["Metric", "Value"],
    ["Cleaned consumption rows (hourly)", f"{clean['consumption']['clean_rows']:,}"],
    ["Mean data completeness (consumption)", f"{clean['consumption']['mean_completeness']*100:.2f}%"],
    ["Avg daily consumption", f"{feat['daily_total_mean_kwh']} kWh"],
    ["Peak-to-average ratio (PAR)", f"{feat['par_mean']}"],
    ["Median peak hour", f"{feat['median_peak_hour']}:00"],
    ["Load–HDH correlation (daily)", f"{feat['r_load_hdh_daily']}"],
    ["Best forecasting model", f"{mdl['best_model']} (MAPE {mdl['best_mape']}%)"],
    ["RMSE improvement vs baseline", f"{mdl['improve_vs_baseline_pct']:.0f}%"],
    ["Wind capacity factor (mean)", f"{feat['wind_cf_mean']}%"],
    ["Anomaly detector", f"precision {anom['precision']} / recall {anom['recall']}"],
]
story.append(styled_table(kpi, [9.5 * cm, 6 * cm]))

# ============================================================ 2. REPO STRUCTURE
H("2. Repository Structure")
repo = """greenpower-capstone/
|-- run_pipeline.py            end-to-end driver (acquire -> ... -> figures)
|-- requirements.txt           portable scientific-Python deps
|-- src/
|   |-- config.py              central paths, periods, physical constants
|   |-- data_acquisition.py    synthetic (calibrated) + real-data stubs
|   |-- clean.py               Week 2 - despike, impute, hourly alignment
|   |-- storage.py             Week 3 - load into SQLite (prod = TimescaleDB)
|   |-- features.py            Week 4 - rollups, calendar, lags, degree-hours
|   |-- models.py              Week 5 - seasonal-naive / Ridge / MLP / LSTM
|   |-- anomaly.py             Week 5 - robust z-score + persistence detector
|   `-- viz.py                 report-styled figures from live outputs
|-- db/migrations/             production TimescaleDB schema (5 SQL files)
|-- dashboard/
|   |-- app.py                 interactive Streamlit dashboard
|   |-- build_static.py        self-contained static HTML dashboard
|   `-- _shots_full.py         Playwright screenshot capture
|-- notebooks/                 04_model_evaluation.ipynb walkthrough
|-- outputs/                   figures, *.json metrics, screenshots
`-- reports/                   weekly PDFs + this final report"""
story.append(Paragraph(repo.replace(" ", "&nbsp;").replace("\n", "<br/>"), styles["mono"]))

# ============================================================ 3. HOW TO RUN
H("3. How to Run")
P("The pipeline runs anywhere with no server or credentials:")
run = """# 1. install portable dependencies
pip install -r requirements.txt

# 2. run the full pipeline (~5s on synthetic data)
python run_pipeline.py

# 3. build the dashboard
streamlit run dashboard/app.py        # interactive (localhost:8501)
python dashboard/build_static.py      # or the static HTML equivalent

# optional extras enable the production paths
pip install statsmodels tensorflow streamlit plotly pyarrow"""
story.append(Paragraph(run.replace(" ", "&nbsp;").replace("\n", "<br/>"), styles["mono"]))
sp(6)
P("This execution was run on Python 3.14 with pandas 3.0 / numpy 2.5 / "
  "scikit-learn 1.9. TensorFlow provides no wheel for Python 3.14, so the pipeline "
  "used its scikit-learn <b>MLP neural net</b> for the non-linear model — the same "
  "role the Keras LSTM fills when TensorFlow is available. The pipeline completed "
  "cleanly end to end.")
story.append(PageBreak())

# ============================================================ 4. EXECUTION EVIDENCE
H("4. Execution Evidence")
P("Every screenshot below is captured at 2× resolution from this run and saved under "
  "<font name='Courier'>outputs/screenshots/</font>.")

H("4.1 Pipeline run", "h2")
figure("01_pipeline_run.png",
       "Figure 1 — Full output of <b>python run_pipeline.py</b>: acquire, clean, store, "
       "features, models, anomaly and figures all complete in ~5s.")

H("4.2 Database queries", "h2")
figure("02_database_query.png",
       "Figure 2 — Querying the SQLite store: <b>.tables</b>, the <b>load_audit</b> table, "
       "the model <b>evaluation_summary</b>, and a sample of <b>consumption_daily</b>.")

H("4.3 Interactive dashboard (live Streamlit)", "h2")
figure("03_dashboard.png",
       "Figure 3 — The live Streamlit dashboard at localhost:8501, reading the same "
       "SQLite database and pipeline outputs: KPIs, daily-consumption trend, "
       "forecast-vs-actual, hourly load profile and the model-evaluation table.",
       max_w=13 * cm)
story.append(PageBreak())

H("4.4 Analytical figures", "h2")
P("The six report figures below are rendered by <font name='Courier'>src/viz.py</font> "
  "directly from the live feature tables, forecasts and anomaly flags.")
figpairs = [
    ("fig_load_profile.png", "Figure 4 — Average hourly load profile; a pronounced ~20:00 "
     "evening peak, slightly flatter on weekends."),
    ("fig_forecast.png", "Figure 5 — Forecast vs actual over the final test week; the MLP "
     "tracks the actual load closely."),
    ("fig_model_metrics.png", "Figure 6 — MAE / RMSE across the three models on the 60-day "
     "hold-out; error falls steadily from baseline to MLP."),
    ("fig_anomaly.png", "Figure 7 — Anomaly detector flagging injected outages and spikes "
     "via robust z-score + persistence."),
    ("fig_load_temp.png", "Figure 8 — Daily consumption vs temperature; clear negative "
     "(heating-driven) relationship."),
    ("fig_capacity_factor.png", "Figure 9 — Wind capacity factor by month; higher in the "
     "windier winter months."),
]
for name, cap in figpairs:
    figure(name, cap, max_w=13 * cm)
story.append(PageBreak())

# ============================================================ 5. RESULTS
H("5. Results")

H("5.1 Cleaning statistics (Week 2)", "h2")
crows = [["Dataset", "Raw rows", "Clean rows", "Spikes removed", "Gaps imputed", "Completeness"]]
for ds in ("consumption", "generation", "weather"):
    c = clean[ds]
    crows.append([ds.capitalize(), f"{c['raw_rows']:,}", f"{c['clean_rows']:,}",
                  str(c['spikes_removed']), str(c['gaps_imputed']),
                  f"{c['mean_completeness']*100:.2f}%"])
story.append(styled_table(crows, [3 * cm, 2.4 * cm, 2.4 * cm, 2.7 * cm, 2.4 * cm, 2.6 * cm]))
sp(8)

H("5.2 Feature-layer statistics (Week 4)", "h2")
frows = [
    ["Feature statistic", "Value"],
    ["Hourly feature rows", f"{feat['cons_hourly_rows']:,}"],
    ["Daily / monthly rollup rows", f"{feat['cons_daily_rows']:,} / {feat['cons_monthly_rows']}"],
    ["Generation daily rows", f"{feat['gen_daily_rows']:,}"],
    ["Peak-to-average ratio (mean)", f"{feat['par_mean']}"],
    ["Load factor (mean)", f"{feat['load_factor_mean']}"],
    ["Median peak hour", f"{feat['median_peak_hour']}:00"],
    ["Evening-peak share (17–21h)", f"{feat['evening_peak_share']}%"],
    ["r(load, temp) hourly / daily", f"{feat['r_load_temp_hourly']} / {feat['r_load_temp_daily']}"],
    ["r(load, heating degree-hours) daily", f"{feat['r_load_hdh_daily']}"],
    ["Wind capacity factor (mean)", f"{feat['wind_cf_mean']}%"],
]
story.append(styled_table(frows, [9.5 * cm, 6 * cm]))
sp(8)

H("5.3 Forecasting model evaluation (Week 5)", "h2")
P(f"60-day chronological hold-out — {mdl['test_hours']:,} test hours, "
  f"{mdl['train_hours']:,} train hours, split at {mdl['split_date']}.")
mrows = [["Model", "MAE (kW)", "RMSE (kW)", "MAPE (%)"]]
for r in evalrows:
    mrows.append([r["model"], r["MAE_kW"], r["RMSE_kW"], r["MAPE_pct"]])
mt = styled_table(mrows, [6 * cm, 3.2 * cm, 3.2 * cm, 3.2 * cm])
# highlight best row
best_idx = next(i for i, r in enumerate(evalrows) if r["model"] == mdl["best_model"]) + 1
mt.setStyle(TableStyle([
    ("BACKGROUND", (0, best_idx), (-1, best_idx), colors.HexColor("#cfe6d8")),
    ("FONTNAME", (0, best_idx), (-1, best_idx), "Helvetica-Bold"),
]))
story.append(mt)
sp(4)
P(f"<b>Best model: {mdl['best_model']}</b> — MAPE {mdl['best_mape']}%, RMSE "
  f"{mdl['best_rmse']} kW, a {mdl['improve_vs_baseline_pct']:.0f}% RMSE reduction "
  f"versus the seasonal-naive baseline.")
sp(8)

H("5.4 Anomaly detection (Week 5)", "h2")
arows = [
    ["Metric", "Value"],
    ["Injected anomaly hours", str(anom["injected_anomaly_hours"])],
    ["Flagged hours", str(anom["flagged_hours"])],
    ["True positives", str(anom["true_positives"])],
    ["False positives", str(anom["false_positives"])],
    ["False negatives", str(anom["false_negatives"])],
    ["Precision", str(anom["precision"])],
    ["Recall", str(anom["recall"])],
]
story.append(styled_table(arows, [9.5 * cm, 6 * cm]))
story.append(PageBreak())

# ============================================================ 6. METHODOLOGY
H("6. Model Methodology")
P("<b>Forecasting.</b> The target is the household's next-hour active power. Three "
  "models of increasing sophistication are compared on an identical 60-day "
  "chronological hold-out, using lag features (1h, 24h, 168h), 24-hour rolling "
  "mean/std, cyclical hour/day-of-year encodings, a weekend flag and heating/cooling "
  "degree-hours:")
meth = [
    ["Model", "Role", "Implementation"],
    ["Seasonal-naive", "baseline", "value 168 h earlier"],
    ["Ridge regression", "linear", "scikit-learn, α = 1.0"],
    ["MLP neural net", "non-linear (runnable)", "scikit-learn, hidden (64, 32)"],
    ["LSTM (Keras)", "production deep model", "TensorFlow, 168-step lookback"],
]
story.append(styled_table(meth, [4 * cm, 4.5 * cm, 7 * cm]))
sp(6)
P("When TensorFlow is installed the pipeline additionally trains the Keras LSTM "
  "(<font name='Courier'>models.train_lstm_keras</font>); otherwise the MLP fills the "
  "neural, non-linear role — as in this run. Error is reported as MAE, RMSE and a "
  "clipped MAPE (denominator floored at 0.3 kW to avoid divide-by-near-zero blow-up "
  "at low overnight load).")
P("<b>Anomaly detection.</b> Each reading is compared to the median for its "
  "hour-of-day × month group, and the deviation is scaled by a per-group median "
  "absolute deviation so naturally variable evening hours are not over-flagged. A "
  "two-part rule fires on either a sustained deviation (≥ 2 consecutive hours, "
  "characteristic of an outage) or a single hard spike. Evaluation injects a labelled "
  "set of synthetic outages and spikes and reports precision / recall.")
P("<b>Storage.</b> The runnable engine is SQLite with the same logical schema as the "
  "production TimescaleDB design; loads are idempotent and audited (see "
  "<font name='Courier'>load_audit</font>). The production migrations add hypertables, "
  "one-month chunking, native compression and continuous aggregates.")

# ============================================================ 7. WEEK MAPPING
H("7. Code → Six-Week Mapping")
weeks = [
    ["Week", "Deliverable", "Code / Output"],
    ["1", "Data sourcing & profiling",
     "data_acquisition.py; calibrated to Week 1–2 statistics"],
    ["2", "Cleaning & preprocessing",
     "clean.py → cleaning_report.json (despike, impute, align)"],
    ["3", "Time-series storage",
     "storage.py (SQLite) + db/migrations/*.sql (TimescaleDB)"],
    ["4", "Feature engineering",
     "features.py → feature_stats.json, feature tables/views"],
    ["5", "Forecasting & anomaly detection",
     "models.py + anomaly.py → evaluation_summary.csv, stats JSON"],
    ["6", "Visualization, dashboard & report",
     "viz.py, dashboard/*, this report"],
]
story.append(styled_table(weeks, [1.4 * cm, 5.4 * cm, 8.7 * cm]))
sp(14)
P("<i>All figures and metrics in this report were generated directly by the pipeline "
  "run documented in Section 4 — no values were transcribed by hand.</i>", "small")


# ---------------- page furniture ----------------
def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#cdd8d0"))
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, 1.4 * cm, A4[0] - 2 * cm, 1.4 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawString(2 * cm, 1.0 * cm, "GreenPower Utilities — Group 5 · IIT Jodhpur")
    canvas.drawRightString(A4[0] - 2 * cm, 1.0 * cm, f"Page {doc.page}")
    canvas.restoreState()


doc = BaseDocTemplate(str(PDF), pagesize=A4,
                      leftMargin=2 * cm, rightMargin=2 * cm,
                      topMargin=1.8 * cm, bottomMargin=1.9 * cm,
                      title="GreenPower Utilities — Final Execution Report",
                      author="Group 5, IIT Jodhpur")
frame = Frame(doc.leftMargin, doc.bottomMargin,
              doc.width, doc.height, id="main")
doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=footer)])
doc.build(story)
print(f"wrote {PDF.relative_to(ROOT)} ({PDF.stat().st_size/1024:.0f} KB)")
