from multiprocessing import Process, Pipe
import logging
import os
import time
import gnsq
import handlers, modem, settings

blacklist = set([])
whitelist = set([])
    
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
            
# TODO: add wildcarding rules
# TODO: add settings load

if __name__ == '__main__':
    currentCall = None
    logging.basicConfig(format='[%(levelname)s %(name)s] %(asctime)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG)
    logger = logging.getLogger('executive')
    logger.setLevel(logging.DEBUG)

    logger.debug('Loading blacklist...')
    load_blacklist('.')
    
    logger.debug('Loading whitelist...')
    load_whitelist('.')
    
    logger.debug('Establishing pub connection to NSQ...')
    pub = gnsq.Nsqd(address='localhost', http_port=4151)
    
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
            if msg[0] == 'B': # append number to blacklist
                blacklist.add(msg[1:])
                if currentCall is not None: # blacklist currently incoming call
                    modem_pipe.send('hangup')
            elif msg[0] == 'W': # append number to whitelist
                whitelist.add(msg[1:])
                
        if modem_pipe.poll(): # incoming call from modem
            currentCall = modem_pipe.recv()
            pub.publish('call_received', currentCall.number)
            if currentCall.number in blacklist:
                modem_pipe.send('hangup')
                currentCall = None
        
        time.sleep(0.1) # keep from using all of the CPU handling messages from threads