import psycopg2
DB_URL = 'postgresql://postgres:gdJpFtONAreX11dK@db.enrxeqcobruhimjukanb.supabase.co:5432/postgres'
try:
    conn = psycopg2.connect(DB_URL)
    with conn.cursor() as cursor:
        cursor.execute("INSERT INTO fleet VALUES ('KA01AD9505', 'B85', 'Electronic City', 'M. Reddy', '98765 43210', '52 Seats') ON CONFLICT (plate) DO NOTHING")
        # Also add with space for normalization check
        cursor.execute("INSERT INTO fleet VALUES ('KA-01 AD-9505', 'B85', 'Electronic City', 'M. Reddy', '98765 43210', '52 Seats') ON CONFLICT (plate) DO NOTHING")
        conn.commit()
        print('SUCCESS: ADDED TEST FLEET')
    conn.close()
except Exception as e:
    print(f'FAILURE: {e}')
