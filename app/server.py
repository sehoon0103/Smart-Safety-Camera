import csv
import time

from flask import Flask, jsonify, request, send_file

app = Flask(__name__)

latest_alert = None  # 최근 알림 저장용 변수


# ===========================================================
# 1) 기본 대시보드 화면 (실시간 상태만 표시)
# ===========================================================
@app.route("/")
def index():
    html = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>스마트 안전 모니터링</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            .status-box {
                border: 2px solid #333; border-radius: 10px;
                padding: 20px; width: 300px; text-align: center;
            }
            .safe { background-color: #d4f7d4; }
            .danger { background-color: #ffcccc; }
        </style>
    </head>
    <body>
        <h1>스마트 안전 모니터링 대시보드</h1>
        <div id="status" class="status-box">
            <h2>상태: <span id="status-text">데이터 없음</span></h2>
            <p id="time-text"></p>
        </div>

        <script>
            function updateStatus() {
                fetch("/get_alert")
                    .then(r => r.json())
                    .then(data => {
                        const box = document.getElementById("status");
                        const txt = document.getElementById("status-text");
                        const timeTxt = document.getElementById("time-text");

                        if (!data || !data.type) {
                            txt.textContent = "데이터 없음";
                            timeTxt.textContent = "";
                            box.className = "status-box";
                            return;
                        }

                        if (data.type === "no_helmet") {
                            box.className = "status-box danger";
                            txt.textContent = "⚠ 안전모 미착용!";
                        } else if (data.type === "ok") {
                            box.className = "status-box safe";
                            txt.textContent = "✅ 정상 (착용)";
                        } else {
                            box.className = "status-box";
                            txt.textContent = "상태: " + data.type;
                        }

                        if (data.time) {
                            const ts = new Date(data.time * 1000);
                            timeTxt.textContent = "감지 시간: " + ts.toLocaleString();
                        }
                    });
            }
            setInterval(updateStatus, 1000);
            updateStatus();
        </script>
    </body>
    </html>
    """
    return html



# ===========================================================
# 2) 라즈베리파이 → 서버 알림 전달 API
# ===========================================================
@app.route("/alert", methods=["POST"])
def alert():
    global latest_alert
    data = request.get_json()
    alert_type = data.get("type", "unknown")

    latest_alert = {
        "type": alert_type,
        "time": time.time()
    }
    print("새 알림 수신:", latest_alert)
    return "ok"



# ===========================================================
# 3) 최근 알림 조회 API
# ===========================================================
@app.route("/get_alert")
def get_alert():
    if latest_alert is None:
        return jsonify({})
    return jsonify(latest_alert)



# ===========================================================
# 4) CSV 파일 그대로 제공 API
# ===========================================================
@app.route("/get_csv")
def get_csv():
    try:
        with open("safety_log.csv", "r", encoding="utf-8") as f:
            return f.read(), 200
    except FileNotFoundError:
        return "CSV file not found", 404



# ===========================================================
# 5) CSV 테이블 페이지 (/logs)
# ===========================================================
@app.route("/logs")
def logs_page():
    rows = []
    try:
        with open("safety_log.csv", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            rows = list(reader)
    except FileNotFoundError:
        header = ["time", "helmet", "vest", "final"]

    html = """
    <html><head>
    <meta charset="utf-8"><title>Smart Safety Log</title>
    <style>
        body { font-family: Arial; padding: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border:1px solid #999; padding: 8px; text-align:center; }
        th { background:#eee; }
        tr:nth-child(even){ background:#f9f9f9; }
    </style>
    </head><body>
    <h2>📒 Smart Safety Log</h2>
    <table><tr>
    """

    for h in header:
        html += f"<th>{h}</th>"
    html += "</tr>"

    for row in rows:
        html += "<tr>"
        for col in row:
            html += f"<td>{col}</td>"
        html += "</tr>"

    html += """
    </table><br>
    <a href="/download_csv">📥 CSV 다운로드</a>
    </body></html>
    """
    return html



# ===========================================================
# 6) CSV 다운로드
# ===========================================================
@app.route("/download_csv")
def download_csv():
    try:
        return send_file("safety_log.csv", as_attachment=True)
    except FileNotFoundError:
        return "CSV 파일 없음"



# ===========================================================
# 7) 그래프 포함 Dashboard 페이지
# ===========================================================
def read_csv():
    result = []
    try:
        with open("safety_log.csv", "r", encoding="utf-8") as f:
            result = list(csv.DictReader(f))
    except FileNotFoundError:
        pass
    return result


@app.route("/dashboard")
def dashboard():

    html = """
    <html>
    <head>
        <meta charset="utf-8">
        <title>Smart Safety Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

        <style>
            body { font-family: Arial; padding: 20px; }

            .card {
                border: 1px solid #ccc;
                padding: 15px;
                border-radius: 10px;
                width: 300px;
                margin-bottom: 20px;
            }

            .safe { background-color: #dfffd8; }
            .warning { background-color: #fff5cc; }
            .danger { background-color: #ffd1d1; }

            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            th, td {
                border: 1px solid #999;
                padding: 8px;
                text-align: center;
            }
            th { background: #f2f2f2; }

        </style>
    </head>

    <body>

        <h1>📊 Smart Safety Dashboard</h1>

        <!-- 상태 카드 -->
        <div id="status_card" class="card">
            <h3>⏱ 시간: <span id="latest_time">-</span></h3>
            <p>🪖 헬멧: <span id="latest_helmet">-</span></p>
            <p>🦺 조끼: <span id="latest_vest">-</span></p>
            <p>⚠ 상태: <span id="latest_final">-</span></p>
        </div>

        <!-- 그래프 -->
        <h2>상태 그래프</h2>
        <canvas id="chart" width="400" height="200"></canvas>

        <!-- 로그 테이블 -->
        <h2>최근 로그</h2>
        <table>
            <tr>
                <th>Time</th>
                <th>Helmet</th>
                <th>Vest</th>
                <th>Final</th>
            </tr>
            <tbody id="log_table"></tbody>
        </table>

        <script>

            let chart = null;

            function updateDashboard() {
                fetch("/dashboard_data")
                .then(r => r.json())
                .then(data => {

                    // -------------------------
                    // 최신 상태 카드 업데이트
                    // -------------------------
                    document.getElementById("latest_time").innerText = data.latest.time;
                    document.getElementById("latest_helmet").innerText = data.latest.helmet;
                    document.getElementById("latest_vest").innerText = data.latest.vest;
                    document.getElementById("latest_final").innerText = data.latest.final;

                    const card = document.getElementById("status_card");
                    card.className = "card " +
                        (data.latest.final === "SAFE" ? "safe"
                         : data.latest.final === "WARNING" ? "warning"
                         : "danger");

                    // -------------------------
                    // 그래프 업데이트
                    // -------------------------
                    let count = data.count;

                    if (chart === null) {
                        const ctx = document.getElementById("chart").getContext("2d");
                        chart = new Chart(ctx, {
                            type: "bar",
                            data: {
                                labels: ["SAFE", "WARNING", "DANGER"],
                                datasets: [{
                                    label: "Count",
                                    data: [count.SAFE, count.WARNING, count.DANGER],
                                    backgroundColor: ["#66dd66", "#ffdd55", "#ff6666"]
                                }]
                            }
                        });
                    } else {
                        chart.data.datasets[0].data = [
                            count.SAFE, count.WARNING, count.DANGER
                        ];
                        chart.update();
                    }


                    // -------------------------
                    // 로그 테이블 업데이트
                    // -------------------------
                    let html = "";
                    for (let row of data.logs) {
                        html += `
                            <tr>
                                <td>${row.time}</td>
                                <td>${row.helmet}</td>
                                <td>${row.vest}</td>
                                <td>${row.final}</td>
                            </tr>
                        `;
                    }
                    document.getElementById("log_table").innerHTML = html;

                });
            }

            // 1초마다 업데이트
            setInterval(updateDashboard, 1000);
            updateDashboard();

        </script>

    </body>
    </html>
    """

    return html



@app.route("/dashboard_data")
def dashboard_data():
    logs = read_csv()

    # 최신 상태 결정
    if logs:
        last = logs[-1]
        latest_info = {
            "time": last["time"],
            "helmet": last["helmet"],
            "vest": last["vest"],
            "final": last["final"],
        }
    else:
        latest_info = {
            "time": "-",
            "helmet": "-",
            "vest": "-",
            "final": "-"
        }

    # 상태 개수 카운트
    count = {"SAFE": 0, "WARNING": 0, "DANGER": 0}
    for row in logs:
        if row["final"] in count:
            count[row["final"]] += 1

    return jsonify({
        "latest": latest_info,
        "count": count,
        "logs": logs[-100:]  # 최근 100개만
    })




# ===========================================================
# 8) 서버 실행 (항상 가장 마지막에 있어야 함)
# ===========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
