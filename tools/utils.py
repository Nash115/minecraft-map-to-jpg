import os
import json

def load_json(filepath, default={}):
    if not os.path.exists(filepath):
        return default
    with open(filepath, 'r') as f:
        return json.load(f)
