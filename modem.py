import serial
import logging

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

class ReceivedCall:
    def __init__(self, date=None, time=None, name=None, number=None):
        self.date = date
        self.time = time
        self.name = name
        self.number = number
        
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
    state = 'idle'
    currentCall = None
    
    while True:
        rx = modem.readline()
        if rx == 'RING\r\n' and state == 'idle':
            logging.info('Incoming call...')
            state = 'wait_cid'
        elif rx[0:4] == 'DATE' and state == 'wait_cid':
            state = 'rx_cid'
            currentCall = ReceivedCall(date=rx[-6:-2])
        elif rx[0:4] == 'TIME':
            currentCall.time = rx[-6:-2]
        elif rx[0:4] == 'NAME':
            currentCall.name = rx[7:-2]
        elif rx[0:4] == 'DDN_':
            currentCall.number = rx[10:-2]
            state = 'wait_decision'
            logging.info('Call received from ' + currentCall.number)
            logging.debug('Waiting for decision...')
            pipe.send(currentCall)
            
            cmd = pipe.recv()
            if cmd == 'hangup':
                modem.write('ATA\r') # 'aggressive' hangup
                state = 'idle'