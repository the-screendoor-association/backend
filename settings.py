import json

# INTERNAL CONSTANTS
nsq_protocol = 'v1.3.1'

# INTERNAL SETTINGS
path_settings = './settings.json'

# USER SETTINGS
registry = {}

def load_settings():
    with open(path_settings, 'r') as sfile:
        global registry
        registry = json.load(sfile)
        
def save_settings():
    with open(path_settings, 'w') as sfile:
        json.dump(registry, sfile)