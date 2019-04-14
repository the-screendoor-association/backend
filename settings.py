import json
import screendoor

# USER SETTINGS
registry = {}
# special runtime user settings not exposed thru Settings menu
filter_disable = False
wildcard_disable = False

def load_settings():
    with open(screendoor.path_settings, 'r') as sfile:
        global registry
        registry = json.load(sfile)
        
def save_settings():
    with open(screendoor.path_settings, 'w') as sfile:
        json.dump(registry, sfile)