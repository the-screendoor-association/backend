import serial
import logging
import settings, screendoor

# sample modem traffic for an incoming call:
# '\r\n'
# 'RING\r\n'
# '\r\n'
# 'DATE = 1124\r\n'
# 'TIME = 1806\r\n'
# 'NAME = O\r\n'
# 'DDN_NMBR= 9196278340\r\n'
# '\r\n'
# 'RING\r\n'
# '\r\n'
# 'RING\r\n'

ok = 'OK\r\n'
        
def modem_init():
    modem = serial.Serial('/dev/ttyACM0', 115200)
    # TODO: handle initialization failures
    
    # reset to factory defaults
    modem.write('ATZ\r')
    resp = ''
    while resp != ok:
        resp = modem.readline()
    
    # disable local echo
    modem.write('ATE0\r')
    resp = ''
    while resp != ok:
        resp = modem.readline()
        
    # enable caller ID reporting
    modem.write('AT+VCID=1\r')
    resp = ''
    while resp != ok:
        resp = modem.readline()
        
    return modem
        
def modem_process(pipe):
    modem = modem_init()
    currentCall = None
    state = 'idle'
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    while True:
        rx = modem.readline()
        if rx == 'RING\r\n' and state == 'idle':
            logger.debug('Incoming call, waiting for CID...')
            state = 'wait_cid'
        elif rx[0:4] == 'DATE' and state == 'wait_cid':
            state = 'rx_cid'
            dateStr = settings.s['year'] + rx[-6:-2]
            currentCall = screendoor.Call(datetime=datestr)
        elif rx[0:4] == 'TIME':
            currentCall.datetime += 'T' + rx[-6:-2]
        elif rx[0:4] == 'NAME':
            currentCall.name = rx[7:-2]
        elif rx[0:4] == 'DDN_':
            currentCall.number = rx[10:-2]
            state = 'wait_decision'
            logger.info('Call received from ' + currentCall.number)
            logger.debug('Waiting for decision...')
            pipe.send(currentCall)
            
            # TODO: at some point we need to timeout for when the user picks up a call or calling party aborts call
            
            cmd = pipe.recv()
            if cmd == 'hangup':
                logger.debug('Hanging up call...')
                modem.write('ATA\r') # begin 'aggressive' hangup
                resp = ''
                while resp != 'NO CARRIER\r\n': # wait for hangup to finish
                    resp = modem.readline()
                
                # call has been hung up, return to idle
                logger.debug('Hangup complete, return to idle')
                currentCall = None
                state = 'idle'