import serial
import logging
from datetime import datetime
import settings, screendoor, relay

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
            year = settings.registry['Calendar year']['current_state']
            dateStr = year + rx[-6:-2] # month day
            currentCall = screendoor.Call(datetime=dateStr)
        elif rx[0:4] == 'TIME':
            currentCall.datetime += 'T' + rx[-6:-2]
        elif rx[0:4] == 'DDN_':
            currentCall.number = screendoor.canonicalize(rx[10:-2])
        elif rx[0:4] == 'NMBR':
            currentCall.number = screendoor.canonicalize(rx[7:-2])
        elif rx[0:4] == 'NAME':
            if rx[7:-2] != 'O': currentCall.name = rx[7:-2]
            else: currentCall.name = 'Unknown name'
        if currentCall.isFull():
            state = 'wait_decision'
            logger.info('Call received from ' + currentCall.number)
            logger.debug('Waiting for decision...')
            pipe.send(currentCall)

            # TODO: need to timeout for when the user picks up a call or calling party aborts call
            
            cmd = pipe.recv()
            if cmd == 'hangup':
                logger.debug('Hanging up call...')
                modem.write('ATA\r') # begin 'aggressive' hangup
                resp = ''
                while resp != 'NO CARRIER\r\n': # wait for hangup to finish
                    resp = modem.readline()
                
                # call has been hung up, return to idle
                logger.debug('Hangup complete, return to idle')
                relay.set_telephone_out_relay_pin(False)
                currentCall = None
                state = 'idle'
            if cmd == 'ans_machine':
                logger.debug('Waiting for RINGs to end...')
                last_ring_time = datetime.now()
                modem.timeout = 5
                while (datetime.now() - last_ring_time).total_seconds() < 5: # wait for no RINGs in the last 5 seconds
                    resp = modem.readline()
                    if resp == 'RING\r\n':
                        last_ring_time = datetime.now()
                
                # RINGs have ended, reconnect telephone out and return to idle
                logger.debug('RINGs have ended, reconnect telephone out and return to idle')
                relay.set_telephone_out_relay_pin(False)
                modem.timeout = None
                currentCall = None
                state = 'idle'
            # this is a quick hack to circumvent some fragility. need a better way.
            elif cmd == 'pass':
                logger.debug('Returning to wait state...')
                currentCall = None
                state = 'idle'
