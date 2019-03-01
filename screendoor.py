# screendoor.py: core classes, methods, internal variables, and bootstrap code.
import os

# INTERNAL PATHS
runtime = '/opt/screendoor/runtime'
path_blacklist = os.path.join(runtime, 'blacklist.txt')
path_wildcards = os.path.join(runtime, 'wildcards.txt')
path_whitelist = os.path.join(runtime, 'whitelist.txt')
path_settings = os.path.join(runtime, 'settings.json')
path_history = os.path.join(runtime, 'history.txt')

class Call:
    def __init__(self, datetime=None, name=None, number=None, wasBlocked='0'):
        self.datetime = datetime
        self.name = name
        self.number = number
        self.wasBlocked = wasBlocked
        
    def __str__(self):
        return ';'.join([self.number, self.name, self.datetime, self.wasBlocked])
    
    def __repr__(self):
        return ';'.join([self.number, self.name, self.datetime, self.wasBlocked])
        
def canonicalize(number):
    if len(number) == 10: number = '1' + number
    return number # canonicalize 10 digit number into 1 + 10digits

if __name__ == '__main__':
    import executive
    executive.start()
