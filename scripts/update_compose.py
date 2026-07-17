import pathlib
p = pathlib.Path('docker-compose.yml')
txt = p.read_text('utf-8')
target = '    volumes:'
replacement = '    command: sh -c "pip install psycopg2-binary && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"\n    volumes:'
if target in txt and replacement not in txt:
    txt = txt.replace(target, replacement)
    p.write_text(txt, 'utf-8')
    print("Success")
else:
    print("Already modified or target not found")
