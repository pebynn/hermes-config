#!/usr/bin/env python3
"""Simple MySQL database viewer - http://localhost:8899"""
import http.server
import json
import urllib.parse
import os
import pymysql

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'stock',
    'password': os.environ.get('MYSQL_STOCK_PASSWORD', 'stock123'),
    'database': 'stock_kline',
    'charset': 'utf8mb4',
}

HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stock DB Viewer</title>
<style>
:root {
  --bg: #ffffff;
  --bg2: #f1f5f9;
  --bg3: #e2e8f0;
  --border: #cbd5e1;
  --text: #0f172a;
  --text2: #475569;
  --text3: #64748b;
  --accent: #0284c7;
  --accent2: #38bdf8;
  --hover: #e2e8f0;
  --card-bg: #f8fafc;
  --btn-bg: #0ea5e9;
  --btn-hover: #0284c7;
  --null: #94a3b8;
  --warn: #d97706;
  --danger: #dc2626;
  --success: #16a34a;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f172a;
    --bg2: #1e293b;
    --bg3: #334155;
    --border: #334155;
    --text: #e2e8f0;
    --text2: #94a3b8;
    --text3: #64748b;
    --accent: #38bdf8;
    --accent2: #0ea5e9;
    --hover: #334155;
    --card-bg: #1e293b;
    --btn-bg: #0ea5e9;
    --btn-hover: #0284c7;
    --null: #475569;
    --warn: #f59e0b;
    --danger: #ef4444;
  }
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, 'Segoe UI', system-ui, sans-serif; background:var(--bg); color:var(--text); }
.header { background:var(--bg2); padding:10px 20px; display:flex; align-items:center; gap:12px; border-bottom:1px solid var(--border); }
.header h1 { font-size:16px; color:var(--accent); }
.header .info { font-size:12px; color:var(--text3); }
.header .nav { margin-left:auto; display:flex; gap:6px; }
.header .nav button { padding:5px 12px; background:var(--bg3); color:var(--text); border:none; border-radius:4px; cursor:pointer; font-size:12px; }
.header .nav button.active { background:var(--accent); color:#fff; }
.layout { display:flex; height:calc(100vh - 45px); }
.sidebar { width:240px; background:var(--bg2); padding:8px; border-right:1px solid var(--border); overflow-y:auto; display:flex; flex-direction:column; gap:4px; }
.sidebar a { display:block; padding:7px 10px; color:var(--text2); text-decoration:none; border-radius:5px; font-size:13px; }
.sidebar a:hover, .sidebar a.active { background:var(--hover); color:var(--text); }
.sidebar .row-count { font-size:11px; color:var(--text3); }
.sidebar .section-title { font-size:11px; color:var(--text3); text-transform:uppercase; letter-spacing:0.5px; padding:8px 10px 4px; margin-top:4px; border-top:1px solid var(--border); }
.main { flex:1; overflow:auto; padding:16px 20px; }
.main h2 { font-size:15px; margin-bottom:12px; color:var(--accent); display:flex; align-items:center; gap:8px; }
.main h2 .badge { font-size:11px; background:var(--bg3); color:var(--text2); padding:2px 8px; border-radius:10px; font-weight:400; }
table.data { width:100%; border-collapse:collapse; font-size:13px; margin-bottom:12px; }
table.data th { background:var(--bg2); padding:5px 8px; text-align:left; border-bottom:2px solid var(--border); position:sticky; top:0; z-index:1; color:var(--text2); font-weight:600; white-space:nowrap; }
table.data th a { color:var(--text2); text-decoration:none; }
table.data th a:hover { color:var(--accent); }
table.data td { padding:5px 8px; border-bottom:1px solid var(--border); max-width:220px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-variant-numeric:tabular-nums; }
table.data tr:hover td { background:var(--hover); }
.pagination { display:flex; gap:6px; margin:12px 0; align-items:center; }
.pagination a { padding:5px 10px; background:var(--bg3); color:var(--text); text-decoration:none; border-radius:4px; font-size:12px; }
.pagination a:hover { background:var(--accent); color:#fff; }
.pagination span { font-size:12px; color:var(--text2); }
.stat-card { background:var(--card-bg); padding:14px 18px; border-radius:8px; border:1px solid var(--border); }
.stat-card .label { font-size:11px; color:var(--text3); margin-bottom:4px; }
.stat-card .value { font-size:22px; font-weight:700; color:var(--accent); }
.stats { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px; }
.col-type { color:var(--text3); font-size:11px; }
.col-null { color:var(--warn); font-size:11px; }

/* SQL Panel */
.sql-panel { display:none; height:100%; flex-direction:column; }
.sql-panel.visible { display:flex; }
.sql-editor { width:100%; min-height:120px; background:var(--bg2); color:var(--text); border:1px solid var(--border); border-radius:6px; padding:10px 12px; font-family:'SF Mono','Fira Code','Cascadia Code',monospace; font-size:13px; resize:vertical; line-height:1.5; }
.sql-editor:focus { outline:none; border-color:var(--accent); }
.sql-toolbar { display:flex; gap:8px; margin:10px 0; align-items:center; }
.sql-toolbar button { padding:6px 16px; background:var(--btn-bg); color:#fff; border:none; border-radius:5px; cursor:pointer; font-size:13px; font-weight:500; }
.sql-toolbar button:hover { background:var(--btn-hover); }
.sql-toolbar .shortcut { font-size:11px; color:var(--text3); }
.sql-toolbar .status { font-size:12px; color:var(--text2); margin-left:8px; }
.sql-toolbar .status.error { color:var(--danger); }
.sql-toolbar .status.ok { color:var(--success); }
.sql-result { flex:1; overflow:auto; }
.sql-result .meta { font-size:12px; color:var(--text3); margin-bottom:8px; }

/* Modal */
.modal-overlay { display:none; position:fixed; top:0;left:0;right:0;bottom:0; background:rgba(0,0,0,0.4); z-index:100; justify-content:center; align-items:center; }
.modal-overlay.visible { display:flex; }
.modal { background:var(--bg); border:1px solid var(--border); border-radius:10px; padding:20px; min-width:400px; max-width:600px; max-height:80vh; overflow:auto; }
.modal h3 { font-size:14px; margin-bottom:12px; color:var(--accent); }
.modal .close { float:right; background:none; border:none; color:var(--text3); cursor:pointer; font-size:18px; }
.modal .row-data { font-family:monospace; font-size:12px; white-space:pre-wrap; max-height:400px; overflow:auto; background:var(--bg2); padding:10px; border-radius:6px; }
</style>
</head>
<body>
<div class="header">
  <h1>📊 Stock DB</h1>
  <span class="info" id="db-info"></span>
  <div class="nav">
    <button id="btn-browse" class="active" onclick="switchTab('browse')">浏览</button>
    <button id="btn-query" onclick="switchTab('query')">SQL</button>
  </div>
</div>
<div class="layout">
  <div class="sidebar" id="sidebar"></div>
  <div class="main" id="main"></div>
  <div class="main sql-panel" id="sql-panel">
    <h2>🔍 SQL Query</h2>
    <textarea class="sql-editor" id="sql-input" placeholder="SELECT * FROM kline WHERE code='sh600519' LIMIT 20&#10;──&#10;Ctrl+Enter to execute" spellcheck="false"></textarea>
    <div class="sql-toolbar">
      <button onclick="runQuery()">▶ Execute</button>
      <span class="shortcut">Ctrl+Enter</span>
      <span class="status" id="sql-status"></span>
    </div>
    <div class="sql-result" id="sql-result"></div>
  </div>
</div>
<div class="modal-overlay" id="row-modal">
  <div class="modal">
    <button class="close" onclick="closeModal()">✕</button>
    <h3>Row Detail</h3>
    <div class="row-data" id="row-detail"></div>
  </div>
</div>
<script>
const API = '/api';
let currentTab = 'browse';
let queryHistory = [];

async function fetchAPI(path, opts) { const r = await fetch(API + path, opts); return r.json(); }

function switchTab(tab) {
  currentTab = tab;
  document.getElementById('btn-browse').classList.toggle('active', tab==='browse');
  document.getElementById('btn-query').classList.toggle('active', tab==='query');
  document.getElementById('main').style.display = tab==='browse'?'block':'none';
  document.getElementById('sql-panel').classList.toggle('visible', tab==='query');
  if (tab==='query') document.getElementById('sql-input').focus();
}

async function loadOverview() {
  const data = await fetchAPI('/overview');
  document.getElementById('db-info').textContent = `stock_kline · ${data.tables.length} tables`;
  let sidebar = data.tables.map(t =>
    `<a href="#" onclick="loadTable('${t.name}');return false">📋 ${t.name} <span class="row-count">${t.rows}</span></a>`
  ).join('');
  document.getElementById('sidebar').innerHTML = sidebar +
    `<div class="section-title">Keyboard</div>
     <a href="#" onclick="switchTab('query');return false">🔍 SQL Query <span class="row-count">Ctrl+Enter</span></a>`;
  
  let html = '<h2>📊 Database Overview</h2><div class="stats">';
  for (const t of data.tables) {
    html += `<div class="stat-card"><div class="label">${t.name}</div><div class="value">${t.rows}</div><div class="label">${t.cols} columns</div></div>`;
  }
  html += '</div><p style="color:var(--text3);font-size:13px">Click a table to browse · Ctrl+Enter for SQL</p>';
  document.getElementById('main').innerHTML = html;
}

async function loadTable(name, page=1, sort='', order='asc') {
  switchTab('browse');
  const data = await fetchAPI(`/table/${name}?page=${page}&sort=${sort}&order=${order}`);
  let html = `<h2>📋 ${name} <span class="badge">~${data.total_rows.toLocaleString()} rows</span></h2>`;
  
  html += '<table class="data"><thead><tr><th>#</th>';
  for (const c of data.columns) {
    html += `<th><a href="#" onclick="loadTable('${name}',${page},'${c.name}','${sort===c.name&&order==='asc'?'desc':'asc'}');return false">${c.name}</a></th>`;
  }
  html += '</tr></thead><tbody>';
  for (let i=0; i<data.rows.length; i++) {
    const row = data.rows[i];
    html += `<tr><td style="color:var(--text3);font-size:11px">${(page-1)*100+i+1}</td>`;
    for (const c of data.columns) {
      const v = row[c.name];
      const title = v !== null ? String(v).replace(/"/g,'&quot;') : 'NULL';
      html += `<td title="${title}" style="cursor:pointer" onclick="showRow(${JSON.stringify(row).replace(/"/g,'&quot;')})">${v !== null ? v : '<i style="color:var(--null)">NULL</i>'}</td>`;
    }
    html += '</tr>';
  }
  html += '</tbody></table>';
  
  const totalPages = Math.ceil(data.total_rows / 100);
  html += '<div class="pagination">';
  if (page > 1) html += `<a href="#" onclick="loadTable('${name}',${page-1},'${sort}','${order}');return false">← Prev</a>`;
  html += `<span>Page ${page} / ${totalPages || 1}</span>`;
  if (page < totalPages) html += `<a href="#" onclick="loadTable('${name}',${page+1},'${sort}','${order}');return false">Next →</a>`;
  html += `<span style="margin-left:auto;font-size:11px;color:var(--text3)">Click row for detail</span>`;
  html += '</div>';
  
  document.getElementById('main').innerHTML = html;
}

function showRow(row) {
  document.getElementById('row-detail').textContent = JSON.stringify(row, null, 2);
  document.getElementById('row-modal').classList.add('visible');
}
function closeModal() { document.getElementById('row-modal').classList.remove('visible'); }
document.getElementById('row-modal').addEventListener('click', function(e) { if (e.target===this) closeModal(); });

async function runQuery() {
  const sql = document.getElementById('sql-input').value.trim();
  if (!sql) return;
  const status = document.getElementById('sql-status');
  const result = document.getElementById('sql-result');
  status.textContent = 'Running...';
  status.className = 'status';
  
  try {
    const r = await fetch(API + '/query', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({sql})
    });
    const data = await r.json();
    
    if (data.error) {
      status.textContent = data.error;
      status.className = 'status error';
      result.innerHTML = '';
      return;
    }
    
    status.textContent = `${data.rows.length} rows · ${data.time_ms}ms`;
    status.className = 'status ok';
    
    if (data.columns.length === 0) {
      result.innerHTML = `<p style="color:var(--text3)">Query executed. ${data.affected_rows||0} rows affected.</p>`;
      return;
    }
    
    let html = `<table class="data"><thead><tr><th>#</th>`;
    for (const c of data.columns) html += `<th>${c}</th>`;
    html += '</tr></thead><tbody>';
    for (let i=0; i<data.rows.length; i++) {
      html += `<tr><td style="color:var(--text3);font-size:11px">${i+1}</td>`;
      for (const c of data.columns) {
        const v = data.rows[i][c];
        html += `<td title="${v!==null?String(v).replace(/"/g,'&quot;'):'NULL'}">${v !== null ? v : '<i style="color:var(--null)">NULL</i>'}</td>`;
      }
      html += '</tr>';
    }
    html += '</tbody></table>';
    result.innerHTML = html;
  } catch(e) {
    status.textContent = 'Network error';
    status.className = 'status error';
  }
}

// Ctrl+Enter shortcut
document.addEventListener('keydown', function(e) {
  if ((e.ctrlKey||e.metaKey) && e.key==='Enter' && currentTab==='query') {
    e.preventDefault();
    runQuery();
  }
  // Ctrl+Shift+F to focus SQL
  if ((e.ctrlKey||e.metaKey) && e.key==='k') {
    e.preventDefault();
    switchTab('query');
  }
});

loadOverview();
</script>
</body>
</html>"""

class DBViewer(http.server.BaseHTTPRequestHandler):
    def get_conn(self):
        return pymysql.connect(**DB_CONFIG)
    
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        
        if path == '/' or path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode())
            return
        
        if path.startswith('/api/'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            api_path = path[4:]
            result = self.handle_api(api_path, qs)
            self.wfile.write(json.dumps(result, default=str).encode())
            return
        
        self.send_response(404)
        self.end_headers()
    
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        if path == '/api/query':
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len)
            data = json.loads(body)
            sql = data.get('sql', '').strip()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            result = self.handle_query(sql)
            self.wfile.write(json.dumps(result, default=str).encode())
            return
        
        self.send_response(404)
        self.end_headers()
    
    def handle_query(self, sql):
        if not sql:
            return {'error': 'Empty query'}
        
        # Basic safety: block destructive operations unless explicitly intended
        sql_upper = sql.upper().strip()
        dangerous = ['DROP', 'TRUNCATE', 'ALTER', 'CREATE', 'RENAME']
        for d in dangerous:
            if sql_upper.startswith(d):
                return {'error': f'Destructive operation ({d}) blocked. Use mysql CLI for schema changes.'}
        
        import time
        conn = self.get_conn()
        try:
            with conn.cursor() as cur:
                start = time.time()
                affected = cur.execute(sql)
                
                # SELECT-like queries
                if cur.description:
                    col_names = [r[0] for r in cur.description]
                    rows = []
                    for row in cur.fetchall():
                        rows.append(dict(zip(col_names, row)))
                    elapsed = int((time.time() - start) * 1000)
                    return {'columns': col_names, 'rows': rows, 'time_ms': elapsed}
                else:
                    # INSERT/UPDATE/DELETE
                    conn.commit()
                    elapsed = int((time.time() - start) * 1000)
                    return {'columns': [], 'rows': [], 'time_ms': elapsed, 'affected_rows': affected}
        except Exception as e:
            return {'error': str(e)}
        finally:
            conn.close()
    
    def handle_api(self, path, qs):
        if path == '/overview':
            conn = self.get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT table_name, table_rows FROM information_schema.tables WHERE table_schema='stock_kline' ORDER BY table_name")
                    tables = []
                    for row in cur.fetchall():
                        cur.execute(f"SELECT COUNT(*) as cnt FROM `{row[0]}`")
                        cnt = cur.fetchone()[0]
                        cur.execute(f"SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='stock_kline' AND table_name='{row[0]}'")
                        cols = cur.fetchone()[0]
                        tables.append({'name': row[0], 'rows': f'{cnt:,}', 'cols': cols})
                    return {'tables': tables}
            finally:
                conn.close()
        
        if path.startswith('/table/'):
            table = path[7:]
            page = int(qs.get('page', [1])[0])
            sort = qs.get('sort', [''])[0]
            order = qs.get('order', ['asc'])[0]
            
            conn = self.get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT column_name, data_type, is_nullable, column_key FROM information_schema.columns WHERE table_schema='stock_kline' AND table_name='{table}' ORDER BY ordinal_position")
                    columns = [{'name': r[0], 'type': r[1], 'nullable': r[2], 'key': r[3]} for r in cur.fetchall()]
                    
                    cur.execute(f"SELECT COUNT(*) FROM `{table}`")
                    total = cur.fetchone()[0]
                    
                    sql = f"SELECT * FROM `{table}`"
                    if sort:
                        sql += f" ORDER BY `{sort}` {order.upper()}"
                    sql += f" LIMIT 100 OFFSET {(page-1)*100}"
                    cur.execute(sql)
                    rows = []
                    col_names = [r[0] for r in cur.description]
                    for row in cur.fetchall():
                        rows.append(dict(zip(col_names, row)))
                    
                    return {'columns': columns, 'rows': rows, 'total_rows': total}
            finally:
                conn.close()
        
        return {'error': 'unknown endpoint'}
    
    def log_message(self, format, *args):
        pass  # quiet

if __name__ == '__main__':
    port = 8899
    server = http.server.HTTPServer(('0.0.0.0', port), DBViewer)
    print(f'DB Viewer running at http://localhost:{port}')
    server.serve_forever()
