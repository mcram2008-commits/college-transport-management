import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Supabase SDK Configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL') or 'https://enrxeqcobruhimjukanb.supabase.co'
SUPABASE_KEY = os.environ.get('SUPABASE_KEY') or 'sb_publishable_SStxaO4YFGGwhUne_C87zA_ip9BeHgu'

if not SUPABASE_URL or not SUPABASE_KEY:
    print("CRITICAL: SUPABASE_URL or SUPABASE_KEY missing!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- DATABASE SETUP (SDK Version) ---
# Note: SDK doesn't support 'CREATE TABLE' directly via standard client. 
# We assume tables exist or are created via Supabase Dashboard.
# For this migration, we'll implement logic that handles missing data gracefully.

def setup_database():
    print("Checking Supabase connection via SDK...")
    try:
        # Simple probe to check connectivity
        supabase.table('admins').select("id").limit(1).execute()
        print("Supabase SDK connection OK.")
        return True
    except Exception as e:
        print(f"Supabase SDK Setup Warning: {e}")
        print("Note: If tables don't exist, please create 'fleet', 'logs', 'admins', 'scanners' in Supabase Dashboard.")
        return False

# --- WEB ROUTES ---

@app.route('/')
def home_page():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    try:
        response = supabase.table('admins')\
            .select('id, name, role')\
            .eq('id', data['id'])\
            .eq('password', data['password'])\
            .execute()
        
        user = response.data[0] if response.data else None
        if user:
            return jsonify(user)
        return jsonify({"error": "Invalid login"}), 401
    except Exception as e:
        print(f"Login Error: {e}")
        return jsonify({"error": "DB unreachable"}), 500

@app.route('/api/fleet', methods=['GET', 'POST'])
def api_fleet_management():
    try:
        if request.method == 'GET':
            response = supabase.table('fleet').select('*').execute()
            return jsonify(response.data)
        
        data = request.json
        # Upsert logic (replace check + insert/update)
        supabase.table('fleet').upsert({
            "plate": data['plate'],
            "serial": data['serial'],
            "route": data['route'],
            "driver": "Authorized",
            "capacity": "50 Seats"
        }).execute()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Fleet Error: {e}")
        return jsonify({"error": "DB unreachable"}), 500

@app.route('/api/fleet/<plate>', methods=['DELETE'])
def api_remove_bus(plate):
    try:
        supabase.table('fleet').delete().eq('plate', plate).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs', methods=['GET'])
def api_all_logs():
    try:
        # Join-like query (if relationships are set up in Supabase)
        # Otherwise, we fetch and merge if needed.
        # Standard: select logs and reference fleet serial/route
        response = supabase.table('logs')\
            .select('*, fleet(serial, route)')\
            .order('id', desc=True)\
            .limit(50)\
            .execute()
        
        # Flatten structure for frontend compatibility
        rows = []
        for r in response.data:
            flat = dict(r)
            if r.get('fleet'):
                flat['serial'] = r['fleet'].get('serial')
                flat['route'] = r['fleet'].get('route')
            rows.append(flat)
            
        return jsonify(rows)
    except Exception as e:
        print(f"Logs Error: {e}")
        return jsonify([]), 500

@app.route('/api/register', methods=['POST'])
def api_register_event():
    data = request.json
    now = datetime.now()
    try:
        supabase.table('logs').insert({
            "plate": data['plate'],
            "type": data['type'],
            "date": str(now.date()),
            "time": str(now.time())
        }).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Register Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def api_system_stats():
    today = str(datetime.now().date())
    try:
        # Entries
        entries = supabase.table('logs').select('id', count='exact').eq('date', today).eq('type', 'ENTRY').execute().count
        # Exits
        exits = supabase.table('logs').select('id', count='exact').eq('date', today).eq('type', 'EXIT').execute().count
        # Total
        total = supabase.table('logs').select('id', count='exact').eq('date', today).execute().count
        # Inside (approx based on net count > 0 per plate)
        # For simplicity in SDK, we'll return fixed or calculate
        inside_res = supabase.table('logs').select('plate, type').execute()
        net_counts = {}
        for l in inside_res.data:
            p = l['plate']
            net_counts[p] = net_counts.get(p, 0) + (1 if l['type'] == 'ENTRY' else -1)
        inside = sum(1 for v in net_counts.values() if v > 0)
        
        scanners = supabase.table('scanners').select('id', count='exact').execute().count
        admins = supabase.table('admins').select('id', count='exact').execute().count
        
        return jsonify({
            "entries": entries, 
            "exits": exits, 
            "total_today": total, 
            "inside": inside, 
            "scanners": scanners, 
            "admins": admins
        })
    except Exception as e:
        print(f"Stats Error: {e}")
        return jsonify({"error": "db hanging"}), 500

@app.route('/api/admins', methods=['GET', 'POST'])
def api_staff_list():
    try:
        if request.method == 'GET':
            response = supabase.table('admins').select('id, name, created').execute()
            return jsonify(response.data)
        
        data = request.json
        supabase.table('admins').insert({
            "id": data['id'],
            "password": data['password'],
            "name": data['id'], # Default name as ID
            "created": str(datetime.now().date())
        }).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admins/<id>', methods=['DELETE'])
def api_fire_staff(id):
    if id == 'admin': return jsonify({"error": "system"}), 400
    try:
        supabase.table('admins').delete().eq('id', id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scanners', methods=['GET', 'POST'])
def api_scanner_nodes():
    try:
        if request.method == 'GET':
            response = supabase.table('scanners').select('*').execute()
            return jsonify(response.data)
        
        data = request.json
        s_id = 'SC' + datetime.now().strftime('%f')[:5]
        supabase.table('scanners').insert({
            "id": s_id,
            "name": data['name'],
            "location": data['location'],
            "status": "Active",
            "added": str(datetime.now().date())
        }).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scanners/<id>', methods=['DELETE'])
def api_del_scanner_node(id):
    try:
        supabase.table('scanners').delete().eq('id', id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    setup_database()
    print("UniTransit Gate Monitoring (HTTP SDK Mode) starting on port 5000")
    # Bind to 0.0.0.0 for Vercel and local network access
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)
