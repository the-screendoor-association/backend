from multiprocessing import Process, Pipe
import logging
import os
import time
import handlers, modem
import gnsq

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
    logging.basicConfig(format='[%(levelname)s] %(asctime)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG)
    logging.debug('Loading blacklist...')
    load_blacklist('.')
    
    logging.debug('Loading whitelist...')
    load_whitelist('.')
    
    logging.debug('Establishing pub connection to NSQ...')
    pub = gnsq.Nsqd(address='localhost', http_port=4151)
    
    logging.debug('Spinning up NSQ handler thread...')
    handler_pipe, handler_child_pipe = Pipe()
    handler_proc = Process(target=handlers.handler_process, args=(handler_child_pipe,))
    handler_proc.start()
    
    logging.debug('Spinning up modem thread...')
    modem_pipe, modem_child_pipe = Pipe()
    modem_proc = Process(target=modem.modem_process, args=(modem_child_pipe,))
    modem_proc.start()
    
    while True:
        if handler_pipe.poll(): # message from NSQ
            msg = handler_pipe.recv()
            if msg[0] == 'B': # append number to blacklist
                blacklist.add(msg[1:])
            elif msg[0] == 'W': # append number to whitelist
                whitelist.add(msg[1:])
                
        if modem_pipe.poll(): # incoming call from modem
            currentCall = modem_pipe.recv()
            pub.publish('call_received', currentCall.number)
        
        time.sleep(0.1) # keep from using all of the CPU handling messages from other thread