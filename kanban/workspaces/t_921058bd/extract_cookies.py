#!/usr/bin/env python3
"""Extract PDD cookies from snap chromium"""
import os, json, sqlite3, tempfile, shutil

cookie_db = os.path.expanduser("~/snap/chromium/common/chromium/Default/Cookies")

if not os.path.exists(cookie_db):
    print(f"Cookie DB not found: {cookie_db}")
    sys.exit(1)

print(f"Cookie DB: {cookie_db} ({os.path.getsize(cookie_db)} bytes)")

# Copy to temp to avoid lock issues
tmp = tempfile.mktemp(suffix='.db')
shutil.copy2(cookie_db, tmp)

try:
    conn = sqlite3.connect(tmp)
    cursor = conn.cursor()
    
    # List pinduoduo cookies
    cursor.execute("""
        SELECT host_key, name, value, path, is_secure, expires_utc, is_httponly
        FROM cookies 
        WHERE host_key LIKE '%pinduoduo%'
        ORDER BY host_key
    """)
    rows = cursor.fetchall()
    
    print(f"\nPDD Cookies found: {len(rows)}")
    
    pdd_cookies = []
    for row in rows:
        host_key, name, value, path, is_secure, expires_utc, is_httponly = row
        print(f"  {host_key:35s} {name:20s} {value[:40]:40s} secure={bool(is_secure)} httponly={bool(is_httponly)}")
        pdd_cookies.append({
            "name": name,
            "value": value,
            "domain": host_key,
            "path": path,
            "secure": bool(is_secure),
            "httpOnly": bool(is_httponly),
            "sameSite": "Lax",
        })
    
    # Also check for mms.pinduoduo specifically  
    cursor.execute("""
        SELECT host_key, name, value, path, is_secure, expires_utc, is_httponly
        FROM cookies 
        WHERE host_key LIKE '%mms%'
        ORDER BY host_key
    """)
    mms_rows = cursor.fetchall()
    print(f"\nMMS cookies: {len(mms_rows)}")
    for row in mms_rows:
        host_key, name, value, path, is_secure, expires_utc, is_httponly = row
        print(f"  {host_key:35s} {name:20s} {value[:40]:40s}")
    
    conn.close()
    
    # Build auth file
    if pdd_cookies:
        auth_data = {
            "cookies": pdd_cookies,
            "origins": []
        }
        auth_path = os.path.expanduser("~/.pdd_auth.json")
        with open(auth_path, "w") as f:
            json.dump(auth_data, f, indent=2)
        print(f"\n✅ Auth file created: {auth_path} ({os.path.getsize(auth_path)} bytes)")
    else:
        print("\n❌ No PDD cookies found in chromium")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    if os.path.exists(tmp):
        os.unlink(tmp)
