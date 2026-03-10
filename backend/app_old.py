from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Database Configuration (Update with your credentials)
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '', # Update this
    'database': 'transport_db'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

# --- DATABASE SETUP ---
def setup_database():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        # Create database if not exists
        cursor.execute("CREATE DATABASE IF NOT EXISTS transport_db")
        cursor.execute("USE transport_db")
        
        # Fleet Table
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
        
        # Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                plate VARCHAR(20),
                type ENUM('ENTRY', 'EXIT'),
                date DATE,
                time TIME,
                FOREIGN KEY (plate) REFERENCES fleet(plate) ON DELETE CASCADE
            )
        """)
        
        # Admin Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id VARCHAR(50) PRIMARY KEY,
                password VARCHAR(50),
                created DATE
            )
        """)
        
        # Initial Admin
        cursor.execute("SELECT COUNT(*) FROM admins")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO admins VALUES (%s, %s, %s)", ('admin', '12345', datetime.now().date()))

        # Scanner Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scanners (
                id VARCHAR(20) PRIMARY KEY,
                name VARCHAR(100),
                location VARCHAR(100),
                status VARCHAR(20),
                added DATE
            )
        """)
        
        # Initial Scanner
        cursor.execute("SELECT COUNT(*) FROM scanners")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO scanners VALUES (%s, %s, %s, %s, %s)", ('SC001', 'Gate 1 Scanner', 'Main Gate', 'Active', datetime.now().date()))

        # Initial Data (optional, only if empty)
        cursor.execute("SELECT COUNT(*) FROM fleet")
        if cursor.fetchone()[0] == 0:
            initial_fleet = [
                ('TN-29 BC-2341', 'B90', 'Dharmapuri', 'M. Senthil', '98450 12345', '55 Seats'),
                ('TN-30 AC-1122', 'B45', 'Salem', 'R. Kumar', '97890 23456', '48 Seats'),
                ('TN-24 BD-5566', 'B12', 'Hosur', 'P. Ravi', '94433 34567', '60 Seats')
            ]
            cursor.executemany("INSERT INTO fleet VALUES (%s, %s, %s, %s, %s, %s)", initial_fleet)
            
        conn.commit()
        cursor.close()
        conn.close()

# --- AUTH ENDPOINTS ---

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB connection failed"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM admins WHERE id = %s AND password = %s", (data['id'], data['password']))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        return jsonify({"id": user['id']})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/admins', methods=['GET'])
def get_admins():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB connection failed"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, created FROM admins")
    admins = cursor.fetchall()
    for a in admins: a['created'] = str(a['created'])
    cursor.close()
    conn.close()
    return jsonify(admins)

@app.route('/api/admins', methods=['POST'])
def add_admin():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB connection failed"}), 500
    cursor = conn.cursor()
    cursor.execute("INSERT INTO admins VALUES (%s, %s, %s)", (data['id'], data['password'], datetime.now().date()))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Admin added"})

@app.route('/api/admins/<id>', methods=['DELETE'])
def delete_admin(id):
    if id == 'admin': return jsonify({"error": "Cannot delete system admin"}), 400
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB connection failed"}), 500
    cursor = conn.cursor()
    cursor.execute("DELETE FROM admins WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Admin deleted"})

# --- SCANNER ENDPOINTS ---

@app.route('/api/scanners', methods=['GET'])
def get_scanners():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB connection failed"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM scanners")
    scanners = cursor.fetchall()
    for s in scanners: s['added'] = str(s['added'])
    cursor.close()
    conn.close()
    return jsonify(scanners)

@app.route('/api/scanners', methods=['POST'])
def add_scanner():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB connection failed"}), 500
    cursor = conn.cursor()
    sc_id = 'SC' + datetime.now().strftime('%f')[:5]
    cursor.execute("INSERT INTO scanners VALUES (%s, %s, %s, %s, %s)", (sc_id, data['name'], data['location'], 'Active', datetime.now().date()))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Scanner added"})

@app.route('/api/scanners/<id>', methods=['DELETE'])
def delete_scanner(id):
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB connection failed"}), 500
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scanners WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Scanner deleted"})

# --- API ENDPOINTS ---

@app.route('/api/fleet', methods=['GET'])
def get_fleet():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB connection failed"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM fleet")
    fleet = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(fleet)

@app.route('/api/fleet', methods=['POST'])
def add_bus():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB connection failed"}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO fleet (plate, serial, route, driver, phone, capacity)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (data['plate'], data['serial'], data['route'], data.get('driver', 'Unknown'), data.get('phone', ''), data.get('capacity', '')))
        conn.commit()
        return jsonify({"message": "Bus added successfully"}), 201
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/api/fleet/<plate>', methods=['DELETE'])
def delete_bus(plate):
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB connection failed"}), 500
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fleet WHERE plate = %s", (plate,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Bus deleted successfully"})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB connection failed"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT l.*, f.serial, f.route, f.driver FROM logs l
        JOIN fleet f ON l.plate = f.plate
        ORDER BY l.id DESC
    """)
    logs = cursor.fetchall()
    for log in logs:
        log['time'] = str(log['time'])
        log['date'] = str(log['date'])
    cursor.close()
    conn.close()
    return jsonify(logs)

@app.route('/api/register', methods=['POST'])
def register_movement():
    data = request.json
    now = datetime.now()
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB connection failed"}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO logs (plate, type, date, time) VALUES (%s, %s, %s, %s)", (data['plate'], data['type'], now.date(), now.time()))
        conn.commit()
        return jsonify({"status": "success"})
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/api/stats', methods=['GET'])
def get_stats():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB connection failed"}), 500
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM logs WHERE date = %s AND type = 'ENTRY'", (today,))
    entries = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM logs WHERE date = %s AND type = 'EXIT'", (today,))
    exits = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT plate, SUM(CASE WHEN type = 'ENTRY' THEN 1 ELSE -1 END) as net
            FROM logs
            GROUP BY plate
            HAVING net > 0
        ) as active
    """)
    inside = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM scanners")
    scanners_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM admins")
    admins_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM logs WHERE date = %s", (today,))
    total_today = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    return jsonify({
        "inside": inside,
        "entries": entries,
        "exits": exits,
        "total_today": total_today,
        "scanners": scanners_count,
        "admins": admins_count
    })


if __name__ == '__main__':
    setup_database()
    app.run(debug=True, port=5000)
