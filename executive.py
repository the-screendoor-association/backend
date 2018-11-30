from multiprocessing import Process, Pipe
import logging
import os
import time
import datetime
import gnsq
import handlers, modem, settings, screendoor

blacklist = set([])
whitelist = set([])
history = []
    
# load blacklist from file
def load_blacklist(path):
    blpath = os.path.join(path, 'blacklist.txt')
    with open(blpath, 'r') as bfile:
        for line in bfile:
            blacklist.add(line.rstrip())
            
# load whitelist from file
def load_whitelist(path):
    wlpath = os.path.join(path, 'whitelist.txt')
    with open(wlpath, 'r') as wfile:
        for line in wfile:
            whitelist.add(line.rstrip())
            
# load history from file
def restore_history(path):
    histpath = os.path.join(path, 'history.txt')
    with open(histpath, 'r') as hfile:
        global history
        for h in list(hfile):
            # datetime;name;number
            sc = h.rstrip().split(';')
            history.append(screendoor.Call(datetime=sc[2], name=sc[1], number=sc[0]))
            
    print 'Restored history:'     
    for h in history: print str(h)
    
    hfile = open(histpath, 'a')
    return hfile
    
def history_to_str(paramsList):
    # nsq sent as strings so coerce to int to perform arithmetic
    numItems = int(paramsList[0])
    offset = int(paramsList[1])
    
    histSlice = history[offset:offset+numItems]
    numReturned = len(histSlice)
    
    returnStr = ':'.join([str(numReturned), str(offset)]) + ':'
    returnStr += ':'.join(str(h) for h in histSlice) # hist is a Call object but we need a str
    
    return returnStr
# TODO: add wildcarding rules
# TODO: add settings load

def start():
    currentCall = None
    logging.basicConfig(format='[%(levelname)s %(name)s] %(asctime)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    logger.debug('Loading blacklist...')
    load_blacklist('.')
    
    logger.debug('Loading whitelist...')
    load_whitelist('.')
    
    logger.debug('Restoring call history...')
    hfile = restore_history('.')
    
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
    
    while True:
        if handler_pipe.poll(): # message from NSQ
            msg = handler_pipe.recv()
            logger.debug('Message from NSQ: ' + str(msg))
            if msg[0] == 'blacklist': # append number to blacklist
                blacklist.add(msg[1])
                if currentCall is not None: # blacklist currently incoming call
                    modem_pipe.send('hangup')
            elif msg[0] == 'whitelist': # append number to whitelist
                whitelist.add(msg[1])
                
            elif msg[0] == 'history':
                resp = history_to_str(msg[1])
                pub.publish('history_give', resp)
                
            elif msg[0] == 'settings_request': # respond to all settings request
                setList = sorted([s['name'] for s in settings.registry.values()])
                pub.publish('settings_all', ':'.join(setList))
            #elif msg[0] == 'setting_get': # respond to single setting request
                # resp = msg[1] # start with setting name
#                 resp += settings.registry[msg[1]]
                
        if modem_pipe.poll(): # incoming call from modem
            currentCall = modem_pipe.recv()

            history.append(currentCall)
            hfile.write(str(currentCall) + '\n')
            
            pub.publish('call_received', currentCall.number + ':' + currentCall.name)
            if currentCall.number in blacklist:
                modem_pipe.send('hangup')
                currentCall = None
                
            # TODO: set currentCall to none if call goes through/is aborted (when phone stops RINGing)
        
        time.sleep(0.05) # keep from using all of the CPU handling messages from threads