# executive.py: core logic for the Screendoor backend.

from multiprocessing import Process, Pipe
import logging
import os
import time
from datetime import datetime
import gnsq
import fnmatch, re
import handlers, modem, settings, screendoor, relay, off_device

# See https://stackoverflow.com/a/17945009.
# Blacklist and whitelist are stored as sets because the "object-is-in" operation is faster with a set than a list.
blacklist = set([])
whitelist = set([])
# History is stored as a list because lists are faster to iterate over than sets.
history = [] # oldest to newest
# Wildcards are stored as a regular expression. See restore_wildcards().
wildcard_rule = ''

### IO METHODS
def load_blacklist():
    """
    Load blacklisted numbers from blacklist.txt.
    Modifies the global blacklist set.
    """
    global blacklist = set([])
    with open(screendoor.path_blacklist, 'r') as bfile:
        for line in bfile:
            blacklist.add(screendoor.canonicalize(line.rstrip()))

def load_whitelist():
    """
    Load whitelisted numbers from whitelist.txt.
    Modifies the global whitelist set.
    """
    global whitelist = set([])
    with open(screendoor.path_whitelist, 'r') as wfile:
        for line in wfile:
            whitelist.add(line.rstrip())

def restore_wildcards():
    """
    Load wildcard rules from wildcards.txt.  
    Modifies the global wildcard regex.
    """
    wildcards = []
    with open(screendoor.path_wildcards, 'r') as wfile:
        for line in list(wfile):
            wildcards.append(line.rstrip())

    # now that we have a list of wildcards, compile into a single regex
    global wildcard_rule = ''
    for w in wildcards:
        # each wildcard is in UNIX shell format. translate it to a regex, group it, and add an OR to chain rules together.
        clause = '({0})|'.format(fnmatch.translate(w))
        wildcard_rule += clause
    wildcard_rule = wildcard_rule[:-1] # get rid of extraneous OR at the end (artifact of iteration)

def restore_history():
    """
    Load call history from history.txt.  
    Modifies the global history list.
    """
    with open(screendoor.path_history, 'r') as hfile:
        global history
        for h in list(hfile):
            # datetime;name;number
            sc = h.rstrip().split(';')
            history.append(screendoor.Call(datetime=sc[2], name=sc[1], number=sc[0],
                wasBlocked=sc[3]))

def append_blacklist(num):
    """
    Appends a blacklisted number to blacklist.txt.

    :param num: string with blacklisted number to append
    """
    with open(screendoor.path_blacklist, 'a') as bfile:
        bfile.write(num + '\n')

def write_blacklist():
    """
    Rewrites blacklist to blacklist.txt

    :param num: string with blacklisted number to append
    """
    with open(screendoor.path_blacklist, 'w') as bfile:
        bfile.write('\n'.join([b for b in blacklist]))
        bfile.write('\n')

def append_history(call):
    """
    Appends a call to the global history list and history.txt.
    Modifies the global history list.

    :param call: Call object to append
    """
    history.append(call)
    with open(screendoor.path_history, 'a') as hfile:
        hfile.write(str(call) + '\n')

### OTHER HELPER METHODS
def history_to_str(paramsList):
    # nsq sent as strings so coerce to int to perform arithmetic
    numItems = int(paramsList[0])
    offset = int(paramsList[1])
    
    # TODO: this is a horrible way to reverse the list, but it beats mutating global state... refactor
    localHist = history[:] # make a shallow copy to avoid reversing the actual history list
    localHist.reverse()
    
    histSlice = localHist[offset:offset+numItems]
    numReturned = len(histSlice)
    
    returnStr = ':'.join([str(numReturned), str(offset), ''])
    returnStr += ':'.join([str(h) for h in histSlice]) # hist is a Call object but we need a str
    
    return returnStr

def blacklist_to_str(paramsList):
    # nsq sent as strings so coerce to int to perform arithmetic
    numItems = int(paramsList[0])
    offset = int(paramsList[1])
    
    localBlacklist = list(blacklist) # copy blacklist set to a list (for indexing purposes)
    localBlacklist.sort() # sort list blacklist (to keep indexes the same across calls)
    
    blacklistSlice = localBlacklist[offset:offset+numItems]
    numReturned = len(blacklistSlice)
    
    returnStr = ':'.join([str(numReturned), str(offset), ''])
    returnStr += ';'.join([b for b in blacklistSlice]) # numbers in blacklist are str, so join them direclty
    
    return returnStr

def matches_wildcard(num):
    """
    Determines whether a number matches a wildcard in the wildcard list.

    :param num: string with number to match
    :returns: True if number matches a rule, False otherwise
    """
    return re.match(wildcard_rule, num) is not None

def start():
    currentCall = None
    logging.basicConfig(format='[%(levelname)s %(name)s] %(asctime)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    logger.debug('Loading blacklist...')
    load_blacklist()
    
    logger.debug('Loading whitelist...')
    load_whitelist()
    
    logger.debug('Restoring call history...')
    restore_history()

    logger.debug('Restoring wildcard rules...')
    restore_wildcards()
    logger.debug('Wildcard rule: ' + wildcard_rule)
    
    logger.debug('Loading settings...')
    settings.load_settings()
    
    logger.debug('Establishing pub connection to NSQ...')
    pub = gnsq.Nsqd(address='localhost', http_port=4151)
    logging.getLogger('urllib3').setLevel(logging.WARNING) # disable annoying urllib3 debugging
    
    logger.debug('Spinning up NSQ handler thread...')
    handler_pipe, handler_child_pipe = Pipe()
    handler_proc = Process(target=handlers.handler_process, args=(handler_child_pipe,))
    handler_proc.start()
    
    logger.debug('Spinning up modem thread...')
    modem_pipe, modem_child_pipe = Pipe()
    modem_proc = Process(target=modem.modem_process, args=(modem_child_pipe,))
    modem_proc.start()
    
    relay.init_relay_gpio()

    pub.publish('heartbeat', 'no')
    last_heartbeat_time = datetime.now()

    while True:
        # heartbeat
        if (datetime.now() - last_heartbeat_time).total_seconds() > 60:
            pub.publish('heartbeat', 'no')
            last_heartbeat_time = datetime.now()

        if handler_pipe.poll(): # message from NSQ
            msg = handler_pipe.recv()
            logger.debug('Message from NSQ: ' + str(msg))
            if msg[0] == 'blacklist': # append number to blacklist
                if msg[1] not in blacklist: # don't add duplicates
                    blacklist.add(msg[1])
                    if currentCall is not None: # blacklist currently incoming call
                        modem_pipe.send('hangup')
                    append_blacklist(msg[1])

            elif msg[0] == 'blacklist_remove':
                if msg[1] in blacklist: # don't do expensive file rewrite if number wasn't in blacklist
                    blacklist.remove(msg[1])
                    write_blacklist() # rewrite blacklist file to reflect removed number

            elif msg[0] == 'whitelist': # append number to whitelist
                whitelist.add(msg[1])
                
            elif msg[0] == 'history':
                resp = history_to_str(msg[1])
                pub.publish('history_give', resp)
                
            elif msg[0] == 'blacklist_get':
                resp = blacklist_to_str(msg[1])
                pub.publish('blacklist_give', resp)
                
            elif msg[0] == 'settings_request': # respond to all settings request
                setList = sorted(settings.registry.keys())
                pub.publish('settings_all', ':'.join(setList))
            elif msg[0] == 'setting_get': # respond to single setting request
                setObj = settings.registry[msg[1]] # single setting requested
                allStates = ';'.join(setObj['states']) # str for all possible states
                
                respList = [msg[1], setObj['help_text'], setObj['current_state'], allStates]
                resp = ':'.join(respList)
                pub.publish('setting_give', resp)
            elif msg[0] == 'setting_set': # change the setting
                # special treatment of off-device programming setting
                if msg[1] == 'Off-device programming':
                    partition = off_device.mount_device()
                    if partition != None:
                        if msg[2] == 'Append':
                            off_device.append_lists(partition)
                        elif msg[2] == 'Replace':
                            off_device.replace_lists(partition)
                        elif msg[2] == 'Export':
                            off_device.copy_lists(partition)
                else:
                    settings.registry[msg[1]]['current_state'] = msg[2]
                    settings.save_settings()
                
        if modem_pipe.poll(): # incoming call from modem
            currentCall = modem_pipe.recv()
            relay.set_ans_machine_relay_pin(False)
            relay.set_telephone_out_relay_pin(False)
            
            mode = settings.registry['Filtering mode']['current_state'] 
            if (mode == 'Blacklist'):
                if (currentCall.number in blacklist) or (matches_wildcard(currentCall.number)):
                    relay.set_telephone_out_relay_pin(True)
                    currentCall.wasBlocked = '1'
                    append_history(currentCall)
                    modem_pipe.send('hangup')
                    currentCall = None
                else:
                    append_history(currentCall)
                    pub.publish('call_received', currentCall.number + ':' + currentCall.name)
                    modem_pipe.send('pass') # this is a hack to get through demo; find better way to get around fragility
                    currentCall = None # part of the above hack; breaks the ability to blacklist while a call is being received
            elif (mode == 'Whitelist'):
                if (currentCall.number in whitelist):
                    append_history(currentCall)
                    pub.publish('call_received', currentCall.number + ':' + currentCall.name)
                    modem_pipe.send('pass') # this is a hack to get through demo; find better way to get around fragility
                    currentCall = None # part of the above hack; breaks the ability to blacklist while a call is being received
                else:
                    relay.set_telephone_out_relay_pin(True)
                    currentCall.wasBlocked = '1'
                    append_history(currentCall)
                    modem_pipe.send('hangup')
                    currentCall = None
            else: # is in Greylist mode, can check, but just assuming for now
                if (currentCall.number in blacklist):
                    relay.set_telephone_out_relay_pin(True)
                    currentCall.wasBlocked = '1'
                    append_history(currentCall)
                    modem_pipe.send('hangup')
                    currentCall = None
                elif (currentCall.number in whitelist):
                    append_history(currentCall)
                    pub.publish('call_received', currentCall.number + ':' + currentCall.name)
                    modem_pipe.send('pass') # this is a hack to get through demo; find better way to get around fragility
                    currentCall = None # part of the above hack; breaks the ability to blacklist while a call is being received
                elif (matches_wildcard(currentCall.number)):
                    relay.set_ans_machine_relay_pin(True)
                    relay.set_telephone_out_relay_pin(True)
                    append_history(currentCall)
                    modem_pipe.send('pass') # this is a hack to get through demo; find better way to get around fragility
                    currentCall = None # part of the above hack; breaks the ability to blacklist while a call is being received
                else:
                    append_history(currentCall)
                    pub.publish('call_received', currentCall.number + ':' + currentCall.name)
                    modem_pipe.send('pass') # this is a hack to get through demo; find better way to get around fragility
                    currentCall = None # part of the above hack; breaks the ability to blacklist while a call is being received

            pub.publish('history_give', history_to_str([10, 0])
            # TODO: set currentCall to none if call goes through/is aborted (when phone stops RINGing)
        
        time.sleep(0.05) # keep from using all of the CPU handling messages from threads
