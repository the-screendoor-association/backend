import json
import screendoor

# USER SETTINGS
registry = {}

def load_settings():
    with open(screendoor.path_settings, 'r') as sfile:
        global registry
        registry = json.load(sfile)
        
def save_settings():
    with open(screendoor.path_settings, 'w') as sfile:
        json.dump(registry, sfile)