# ===== IMPORT =====
import os, time, json, asyncio
from html import escape
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from zoneinfo import ZoneInfo
from urllib.parse import urlencode

from fastapi import FastAPI, Query, HTTPException, Form, WebSocket
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from dotenv import load_dotenv
import uvicorn

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import qrcode

from db import *

# ===== ENV =====
load_dotenv()
PORT = int(os.getenv("PORT", "8080"))
BEIJING_TZ = ZoneInfo("Asia/Shanghai")

# ===== SESSION FILE =====
SESSION_FILE = "sessions.json"

def load_sessions():
    try:
        return json.load(open(SESSION_FILE))
    except:
        return {}

def save_sessions(s):
    json.dump(s, open(SESSION_FILE,"w"))

SESSIONS = load_sessions()

# ===== APP =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

# ===== LOGIN =====
@app.get("/login", response_class=HTMLResponse)
def login_page():
    return """
    <form method="post" style="padding:80px">
        <h2>VIP LOGIN</h2>
        <input name="user"><br><br>
        <input name="password" type="password"><br><br>
        <button>Login</button>
    </form>
    """

@app.post("/login")
def do_login(user: str = Form(...), password: str = Form(...)):
    if user=="vip" and password=="000":
        token=str(time.time())
        SESSIONS[token]=True
        save_sessions(SESSIONS)
        return RedirectResponse(f"/vip000.bot?session={token}",303)
    return HTMLResponse("Login fail",401)

def require_login(session):
    if session not in SESSIONS:
        raise HTTPException(401)

# ===== DASHBOARD =====
def page(body):
    return HTMLResponse(f"""
    <html>
    <head>
    <style>
    body{{background:#0f172a;color:white;font-family:Arial}}
    .card{{padding:20px;margin:10px;background:#1e293b;border-radius:16px;
    box-shadow:0 0 30px rgba(37,99,235,.3)}}
    </style>
    </head>
    <body>{body}</body>
    </html>
    """)

@app.get("/vip000.bot")
def dashboard(session: str = Query(None)):
    require_login(session)

    stats = get_dashboard_stats()

    body=f"""
    <h1>VIP DASHBOARD</h1>

    <div class="card">Users: {stats["total_users"]}</div>
    <div class="card">Active: {stats["active_users"]}</div>

    <div class="card">
    <a href="/export/pdf">🧾 Export PDF</a>
    </div>

    <div class="card">
    <canvas id="chart"></canvas>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    fetch('/api/stats').then(r=>r.json()).then(d=>{
        new Chart(document.getElementById('chart'),{{
            type:'bar',
            data:{{
                labels:d.map(x=>x.date),
                datasets:[{{label:'Income',data:d.map(x=>x.value)}}]
            }}
        })
    })
    </script>
    """

    return page(body)

# ===== API =====
@app.get("/api/stats")
def stats():
    now=datetime.now(BEIJING_TZ)
    arr=[]
    for i in range(7):
        arr.append({"date":str(i),"value":i*10})
    return arr

# ===== PDF =====
@app.get("/export/pdf")
def export_pdf():
    path="/mnt/data/vip.pdf"
    doc=SimpleDocTemplate(path)
    el=[]

    el.append(Paragraph("VIP REPORT", getSampleStyleSheet()["Title"]))

    qr=qrcode.make("VIP VERIFY")
    qr.save("/mnt/data/qr.png")
    el.append(Image("/mnt/data/qr.png",100,100))

    data=[["User","Amount"]]
    txs=get_transactions(None)
    for t in txs:
        data.append([str(t[3]),str(t[8])])

    table=Table(data)
    table.setStyle(TableStyle([("GRID",(0,0),(-1,-1),1,colors.black)]))

    el.append(table)
    doc.build(el)

    return FileResponse(path)

# ===== WS =====
@app.websocket("/ws")
async def ws(ws:WebSocket):
    await ws.accept()
    while True:
        await ws.send_json(get_dashboard_stats())
        await asyncio.sleep(3)

# ===== ROOT =====
@app.get("/")
def home():
    return RedirectResponse("/login")

# ===== RUN =====
if __name__ == "__main__":
    uvicorn.run("web_vip:app", host="0.0.0.0", port=PORT)
