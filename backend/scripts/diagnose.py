import sys, json, sqlite3, os
sys.stdout.reconfigure(encoding='utf-8')

for db_path in ['iris.db', 'data/iris.db']:
    if not os.path.exists(db_path):
        print(f"DB not found: {db_path}")
        continue
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(f"\n=== DB: {db_path} ({os.path.getsize(db_path)} bytes) ===")
        print(f"Tables: {tables}")

        if 'documents' in tables:
            cur.execute("SELECT id, name, document_type, category, status, is_locked, LENGTH(COALESCE(extracted_json,'')) FROM documents")
            rows = cur.fetchall()
            print(f"\nDocuments ({len(rows)}):")
            for r in rows:
                doc_id, name, dtype, cat, status, locked, json_len = r
                print(f"  [{doc_id[:8]}] {name}")
                print(f"    type={dtype} | cat={cat} | status={status} | locked={locked} | json_bytes={json_len}")

        if 'users' in tables:
            cur.execute("SELECT id, email FROM users")
            users = cur.fetchall()
            print(f"\nUsers: {users}")

        conn.close()
    except Exception as e:
        print(f"ERROR reading {db_path}: {e}")

# Check vector store
print("\n=== VECTOR STORE ===")
vstore = 'vector_store'
if os.path.exists(vstore):
    for root, dirs, files in os.walk(vstore):
        for f in files:
            fp = os.path.join(root, f)
            print(f"  {fp} ({os.path.getsize(fp)} bytes)")
else:
    print("vector_store directory not found")

# Check uploads
print("\n=== UPLOADS DIR ===")
if os.path.exists('uploads'):
    for root, dirs, files in os.walk('uploads'):
        for f in files:
            fp = os.path.join(root, f)
            print(f"  {fp} ({os.path.getsize(fp)} bytes)")
else:
    print("uploads directory not found or empty")
