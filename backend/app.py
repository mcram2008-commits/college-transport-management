import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Supabase Connection (Update your environment variables in Vercel!)
def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        db_url = 'postgresql://postgres:gdJpFtONAreX11dK@db.enrxeqcobruhimjukanb.supabase.co:5432/postgres'
        
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"PostgreSQL ERROR ({db_url[:20]}...): {e}")
        return None

def setup_database():
    print("Checking Supabase database structure...")
    conn = get_db_connection()
    if not conn:
        print("CRITICAL: Failed to connect to Supabase database. Check your DATABASE_URL.")
        return False
        
    try:
        with conn.cursor() as cursor:
            # Tables creation (Postgres syntax)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fleet (
                    plate VARCHAR(20) PRIMARY KEY,
                    serial VARCHAR(20),
                    route VARCHAR(100),
                    driver VARCHAR(100),
                    phone VARCHAR(20),
                    capacity VARCHAR(20)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id SERIAL PRIMARY KEY,
                    plate VARCHAR(20),
                    type VARCHAR(10),
                    date DATE,
                    time TIME,
                    FOREIGN KEY (plate) REFERENCES fleet(plate) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id VARCHAR(50) PRIMARY KEY,
                    password VARCHAR(50),
                    name VARCHAR(100),
                    role VARCHAR(20) DEFAULT 'admin',
                    created DATE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scanners (
                    id VARCHAR(20) PRIMARY KEY,
                    name VARCHAR(100),
                    location VARCHAR(100),
                    status VARCHAR(20),
                    added DATE
                )
            """)

            # Initial Admin
            cursor.execute("SELECT id FROM admins WHERE id = 'admin'")
            if not cursor.fetchone():
                print("Setting up default admin account in Supabase...")
                cursor.execute("INSERT INTO admins (id, password, name, role, created) VALUES (%s, %s, %s, %s, %s)", 
                               ('admin', '12345', 'System Admin', 'admin', datetime.now().date()))

            cursor.execute("SELECT id FROM admins WHERE id = 'cam01'")
            if not cursor.fetchone():
                print("Setting up default scanner account in Supabase...")
                cursor.execute("INSERT INTO admins (id, password, name, role, created) VALUES (%s, %s, %s, %s, %s)", 
                               ('cam01', 'scan123', 'Gate Camera 1', 'scanner', datetime.now().date()))

            # Demo fleet
            cursor.execute("SELECT plate FROM fleet LIMIT 1")
            if not cursor.fetchone():
                print("Populating initial bus fleet in Supabase...")
                initial_fleet = [
                    ('TN-29 BC-2341', 'B90', 'Dharmapuri', 'M. Senthil', '98450 12345', '55 Seats'),
                    ('TN-30 AC-1122', 'B45', 'Salem', 'R. Kumar', '97890 23456', '48 Seats'),
                    ('TN-24 BD-5566', 'B12', 'Hosur', 'P. Ravi', '94433 34567', '60 Seats'),
                    ('KA-01 AD-9505', 'B85', 'Electronic City', 'M. Reddy', '98765 43210', '52 Seats')
                ]
                for bus in initial_fleet:
                    cursor.execute("INSERT INTO fleet VALUES (%s, %s, %s, %s, %s, %s)", bus)
            
            conn.commit()
            print("Supabase structure OK.")
            return True
    except Exception as e:
        print(f"Setup error on Supabase: {e}")
        return False
    finally:
        conn.close()

# --- WEB ROUTES ---

@app.route('/')
def home_page():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB unreachable"}), 500
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id, name, role FROM admins WHERE id = %s AND password = %s", (data['id'], data['password']))
            user = cursor.fetchone()
            if user: return jsonify(user)
            return jsonify({"error": "Invalid login"}), 401
    finally:
        conn.close()

@app.route('/api/fleet', methods=['GET', 'POST'])
def api_fleet_management():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB unreachable"}), 500
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            if request.method == 'GET':
                cursor.execute("SELECT * FROM fleet")
                return jsonify(cursor.fetchall())
            
            data = request.json
            # Use ON CONFLICT (plate) DO UPDATE for PostgreSQL
            cursor.execute("""
                INSERT INTO fleet (plate, serial, route, driver, capacity) 
                VALUES (%s, %s, %s, %s, %s) 
                ON CONFLICT (plate) DO UPDATE SET serial=EXCLUDED.serial, route=EXCLUDED.route
            """, (data['plate'], data['serial'], data['route'], 'Authorized', '50 Seats'))
            conn.commit()
            return jsonify({"success": True})
    finally:
        conn.close()

@app.route('/api/fleet/<plate>', methods=['DELETE'])
def api_remove_bus(plate):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM fleet WHERE plate = %s", (plate,))
            conn.commit()
            return jsonify({"success": True})
    finally:
        conn.close()

@app.route('/api/logs', methods=['GET'])
def api_all_logs():
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT l.*, f.serial, f.route 
                FROM logs l 
                LEFT JOIN fleet f ON l.plate = f.plate 
                ORDER BY l.id DESC LIMIT 50
            """)
            rows = cursor.fetchall()
            for r in rows:
                r['date'] = str(r['date'])
                r['time'] = str(r['time'])
            return jsonify(rows)
    finally:
        conn.close()

@app.route('/api/register', methods=['POST'])
def api_register_event():
    data = request.json
    now = datetime.now()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            print(f"DEBUG: Registering event for {data.get('plate')} - {data.get('type')}")
            cursor.execute("INSERT INTO logs (plate, type, date, time) VALUES (%s,%s,%s,%s)", (data['plate'], data['type'], now.date(), now.time()))
            conn.commit()
            return jsonify({"status": "success"})
    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/stats', methods=['GET'])
def api_system_stats():
    today = datetime.now().date()
    conn = get_db_connection()
    if not conn: return jsonify({"error": "db hanging"}), 500
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM logs WHERE date = %s AND type = 'ENTRY'", (today,))
            entries = cursor.fetchone()['count']
            cursor.execute("SELECT COUNT(*) as count FROM logs WHERE date = %s AND type = 'EXIT'", (today,))
            exits = cursor.fetchone()['count']
            cursor.execute("SELECT COUNT(*) as count FROM logs WHERE date = %s", (today,))
            total = cursor.fetchone()['count']
            cursor.execute("""
                SELECT COUNT(*) as count FROM (
                    SELECT plate, SUM(CASE WHEN type = 'ENTRY' THEN 1 ELSE -1 END) as net 
                    FROM logs GROUP BY plate HAVING SUM(CASE WHEN type = 'ENTRY' THEN 1 ELSE -1 END) > 0
                ) t
            """)
            inside = cursor.fetchone()['count']
            cursor.execute("SELECT COUNT(*) as count FROM scanners")
            scanners = cursor.fetchone()['count']
            cursor.execute("SELECT COUNT(*) as count FROM admins")
            admins = cursor.fetchone()['count']
            return jsonify({"entries": entries, "exits": exits, "total_today": total, "inside": inside, "scanners": scanners, "admins": admins})
    finally:
        conn.close()

@app.route('/api/admins', methods=['GET', 'POST'])
def api_staff_list():
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            if request.method == 'GET':
                cursor.execute("SELECT id, name, created FROM admins")
                res = cursor.fetchall()
                for r in res: r['created'] = str(r['created'])
                return jsonify(res)
            
            data = request.json
            cursor.execute("INSERT INTO admins (id, password, name, created) VALUES (%s,%s,%s,%s)", 
                           (data['id'], data['password'], data['id'], datetime.now().date()))
            conn.commit()
            return jsonify({"success": True})
    finally:
        conn.close()

@app.route('/api/admins/<id>', methods=['DELETE'])
def api_fire_staff(id):
    if id == 'admin': return jsonify({"error": "system"}), 400
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM admins WHERE id=%s", (id,))
            conn.commit()
            return jsonify({"success": True})
    finally:
        conn.close()

@app.route('/api/scanners', methods=['GET', 'POST'])
def api_scanner_nodes():
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            if request.method == 'GET':
                cursor.execute("SELECT * FROM scanners")
                res = cursor.fetchall()
                for r in res: r['added'] = str(r['added'])
                return jsonify(res)
            
            data = request.json
            s_id = 'SC' + datetime.now().strftime('%f')[:5]
            cursor.execute("INSERT INTO scanners (id, name, location, status, added) VALUES (%s,%s,%s,%s,%s)", 
                           (s_id, data['name'], data['location'], 'Active', datetime.now().date()))
            conn.commit()
            return jsonify({"success": True})
    finally:
        conn.close()

@app.route('/api/scanners/<id>', methods=['DELETE'])
def api_del_scanner_node(id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM scanners WHERE id=%s", (id,))
            conn.commit()
            return jsonify({"success": True})
    finally:
        conn.close()

if __name__ == '__main__':
    print("Pre-start: Initializing system using Supabase (PostgreSQL)...")
    setup_database()
    print("UniTransit Gate Monitoring starting on http://10.192.3.52:5000")
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)
