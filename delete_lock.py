import os
p = r'C:\Projects\Pranely\packages\frontend\package-lock.json'
print('Exists:', os.path.exists(p))
if os.path.exists(p):
    os.remove(p)
    print('Deleted:', not os.path.exists(p))
else:
    print('Already deleted')
