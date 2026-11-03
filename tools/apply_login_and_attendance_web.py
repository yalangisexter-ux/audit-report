# Neutralized: this one-shot apply script previously contained nested triple-quoted
# SQL strings and caused `python -m compileall` to fail in Master Build.
# Content moved to apply_login_and_attendance_web.py.broken.txt for archaeology.
# Runtime attendance/login fixes live in api_server.py and web_auth_shim.py.
raise SystemExit("This apply script is retired. Use current api_server.py / web_auth_shim.py.")
