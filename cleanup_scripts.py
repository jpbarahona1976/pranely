import os
scripts = [
    'C:/Projects/Pranely/delete_lock.py',
    'C:/Projects/Pranely/build_frontend.py',
    'C:/Projects/Pranely/build_frontend_clean.py',
    'C:/Projects/Pranely/build_frontend_fresh.py',
    'C:/Projects/Pranely/build_frontend_legacy.py',
    'C:/Projects/Pranely/start_containers.py',
    'C:/Projects/Pranely/check_bridge.py'
]
for s in scripts:
    if os.path.exists(s):
        os.remove(s)
print("Cleanup done")
