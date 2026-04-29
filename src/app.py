from flask import Flask, jsonify, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix
import pymysql
import pymysql.cursors

app = Flask(__name__, template_folder="templates")
app.wsgi_app = ProxyFix(app.wsgi_app)

DB = dict(
    host="localhost",
    user="alphaess",
    password="alphaess123",
    db="alphaess",
    charset="utf8mb4",
)

def get_conn():
    return pymysql.connect(**DB)

# ─── Pages ───────────────────────────────────────────────────────────────────

@app.route("/monitor")
@app.route("/monitor/")
def index():
    return render_template("index.html")

# ─── API ─────────────────────────────────────────────────────────────────────

@app.route("/monitor/api/inverter")
def api_inverter():
    hours = int(request.args.get("hours", 3))
    conn = get_conn()
    with conn.cursor(pymysql.cursors.DictCursor) as c:
        c.execute("""
            SELECT ts,
                bat_soc, bat_soh, bat_status,
                bat_power_w, bat_voltage_v, bat_current_a,
                bat_temp_min_c, bat_temp_max_c,
                pv_power_w, pv1_power_w, pv2_power_w, pv3_power_w,
                pv1_voltage_v, pv1_current_a,
                pv2_voltage_v, pv2_current_a,
                pv3_voltage_v, pv3_current_a,
                inv_temp_c, inv_work_mode,
                grid_power_w, grid_voltage_v, grid_freq_hz,
                grid_energy_feed_kwh, grid_energy_consume_kwh,
                grid_export_pct
            FROM inverter_status
            WHERE ts >= NOW() - INTERVAL %s HOUR
            ORDER BY ts ASC
        """, (hours,))
        rows = c.fetchall()
    conn.close()
    for r in rows:
        r["ts"] = r["ts"].isoformat()
    return jsonify(rows)

@app.route("/monitor/api/inverter/latest")
def api_inverter_latest():
    conn = get_conn()
    with conn.cursor(pymysql.cursors.DictCursor) as c:
        c.execute("""
            SELECT * FROM inverter_status
            ORDER BY ts DESC LIMIT 1
        """)
        row = c.fetchone()
    conn.close()
    if row:
        row["ts"] = row["ts"].isoformat()
    return jsonify(row or {})

@app.route("/monitor/api/prices")
def api_prices():
    conn = get_conn()
    with conn.cursor(pymysql.cursors.DictCursor) as c:
        c.execute("""
            SELECT ts_start, ts_end, price_ct FROM prices
            WHERE ts_end >= NOW() - INTERVAL 6 HOUR
            ORDER BY ts_start ASC
        """)
        rows = c.fetchall()
    conn.close()
    for r in rows:
        r["ts_start"] = r["ts_start"].isoformat()
        r["ts_end"]   = r["ts_end"].isoformat()
    return jsonify(rows)

@app.route("/monitor/api/actions")
def api_actions():
    conn = get_conn()
    with conn.cursor(pymysql.cursors.DictCursor) as c:
        c.execute("""
            SELECT ts, action, reason, value FROM control_actions
            ORDER BY ts DESC LIMIT 50
        """)
        rows = c.fetchall()
    conn.close()
    for r in rows:
        r["ts"] = r["ts"].isoformat()
    return jsonify(rows)

# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6784, debug=False)
