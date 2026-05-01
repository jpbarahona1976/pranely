import os
for f in ['C:/Projects/Pranely/docker_up.py']:
    if os.path.exists(f):
        os.remove(f)
print("Done")
