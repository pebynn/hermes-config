#!/usr/bin/env python3
"""Simple MySQL database viewer - http://localhost:8899
Run with: /home/pebynn/tools/quant_env/bin/python3 db_viewer.py
(quant_env has pymysql; system python3 does not)
"""
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
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, 'Segoe UI', sans-serif; background:#0f172a; color:#e2e8f0; }
.header { background:#1e293b; padding:12px 20px; display:flex; align-items:center; gap:16px; border-bottom:1px solid #334155; }
.header h1 { font-size:18px; color:#38bdf8; }
.header .info { font-size:12px; color:#94a3b8; }
.layout { display:flex; height:calc(100vh - 49px); }
.sidebar { width:240px; background:#1e293b; padding:8px; border-right:1px solid #334155; overflow-y:auto; }
.sidebar a { display:block; padding:8px 12px; color:#94a3b8; text-decoration:none; border-radius:6px; font-size:13px; }
.sidebar a:hover, .sidebar a.active { background:#334155; color:#e2e8f0; }
.sidebar .table-count { font-size:11px; color:#64748b; margin-left:4px; }
.main { flex:1; overflow:auto; padding:16px; }
.main h2 { font-size:16px; margin-bottom:12px; color:#38bdf8; }
table.data { width:100%; border-collapse:collapse; font-size:13px; }
table.data th { background:#1e293b; padding:6px 10px; text-align:left; border-bottom:2px solid #334155; position:sticky; top:0; z-index:1; color:#94a3b8; font-weight:600; }
table.data td { padding:6px 10px; border-bottom:1px solid #1e293b; max-width:250px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
table.data tr:hover td { background:#1e293b; }
.pagination { display:flex; gap:8px; margin:16px 0; align-items:center; }
.pagination a { padding:6px 12px; background:#334155; color:#e2e8f0; text-decoration:none; border-radius:4px; font-size:13px; }
.pagination a:hover { background:#475569; }
.pagination span { font-size:13px; color:#94a3b8; }
.stat-card { background:#1e293b; padding:16px; border-radius:8px; margin-bottom:12px; }
.stat-card .label { font-size:12px; color:#64748b; }
.stat-card .value { font-size:24px; font-weight:700; color:#38bdf8; }
.stats { display:flex; gap:16px; flex-wrap:wrap; margin-bottom:20px; }
.col-type { color:#64748b; font-size:11px; }
.col-null { color:#f59e0b; font-size:11px; }
</style>
</head>
<body>
<div class="header">
  <h1>📊 Stock DB Viewer</h1>
  <span class="info" id="db-info"></span>
</div>
<div class="layout">
  <div class="sidebar" id="sidebar"></div>
  <div class="main" id="main"></div>
</div>
<script>
const API = '/api';
async function fetchAPI(path) { const r = await fetch(API + path); return r.json(); }

async function loadOverview() {
  const data = await fetchAPI('/overview');
  document.getElementById('db-info').textContent = `stock_kline · ${data.tables.length} tables`;
  let sidebar = data.tables.map(t => `<a href="#" onclick="loadTable('${t.name}');return false">📋 ${t.name} <span class="table-count">${t.rows}</span></a>`).join('');
  document.getElementById('sidebar').innerHTML = sidebar;
  
  let html = '<h2>📊 Database Overview</h2><div class="stats">';
  for (const t of data.tables) {
    html += `<div class="stat-card"><div class="label">${t.name}</div><div class="value">${t.rows}</div><div class="label">${t.cols} columns</div></div>`;
  }
  html += '</div><p style="color:#64748b">Click a table in the sidebar to browse data.</p>';
  document.getElementById('main').innerHTML = html;
}

async function loadTable(name, page=1, sort='', order='asc') {
  const data = await fetchAPI(`/table/${name}?page=${page}&sort=${sort}&order=${order}`);
  let html = `<h2>📋 ${name} <span style="font-size:13px;color:#64748b">~${data.total_rows} rows</span></h2>`;
  
  html += '<h3 style="margin-top:16px;color:#94a3b8;font-size:14px;">Schema</h3><table class="data"><tr><th>Column</th><th>Type</th><th>Key</th><th>Nullable</th></tr>';
  for (const c of data.columns) {
    html += `<tr><td>${c.name}</td><td class="col-type">${c.type}</td><td>${c.key||''}</td><td class="col-null">${c.nullable}</td></tr>`;
  }
  html += '</table>';
  
  if (data.columns.length > 0 && data.rows.length > 0) {
    html += '<h3 style="margin-top:20px;color:#94a3b8;font-size:14px;">Data</h3><table class="data"><tr>';
    for (const c of data.columns) {
      html += `<th><a href="#" onclick="loadTable('${name}',${page},'${c.name}','${sort===c.name&&order==='asc'?'desc':'asc'}');return false">${c.name}</a></th>`;
    }
    html += '</tr>';
    for (const row of data.rows) {
      html += '<tr>';
      for (const c of data.columns) {
        const v = row[c.name];
        html += `<td title="${v}">${v !== null ? v : '<i style="color:#475569">NULL</i>'}</td>`;
      }
      html += '</tr>';
    }
    html += '</table>';
    
    const totalPages = Math.ceil(data.total_rows / 100);
    html += '<div class="pagination">';
    if (page > 1) html += `<a href="#" onclick="loadTable('${name}',${page-1},'${sort}','${order}');return false">← Prev</a>`;
    html += `<span>Page ${page} / ${totalPages}</span>`;
    if (page < totalPages) html += `<a href="#" onclick="loadTable('${name}',${page+1},'${sort}','${order}');return false">Next →</a>`;
    html += '</div>';
  } else {
    html += '<p style="color:#64748b;margin-top:12px">No data in this table.</p>';
  }
  
  document.getElementById('main').innerHTML = html;
}

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
            
            api_path = path[4:]  # strip /api, keeps leading /
            result = self.handle_api(api_path, qs)
            self.wfile.write(json.dumps(result, default=str).encode())
            return
        
        self.send_response(404)
        self.end_headers()
    
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
