import gnsq
import logging
import multiprocessing
import settings

backend_conn = None
backend_lock = None

def handler_process(pipe):
    global backend_conn, backend_lock
    backend_conn = pipe
    backend_lock = multiprocessing.Lock()
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    logger.debug('Establishing subscriptions to NSQ topics...')
    logging.getLogger('gnsq').setLevel(logging.INFO)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    cb_reader = gnsq.Reader('call_blacklist', 'backend_py', '127.0.0.1:4150')
    cw_reader = gnsq.Reader('call_whitelist', 'backend_py', '127.0.0.1:4150')
    hg_reader = gnsq.Reader('history_get', 'backend_py', '127.0.0.1:4150')
    sr_reader = gnsq.Reader('settings_request_all', 'backend_py', '127.0.0.1:4150')
    sg_reader = gnsq.Reader('setting_get', 'backend_py', '127.0.0.1:4150')
    ss_reader = gnsq.Reader('setting_set', 'backend_py', '127.0.0.1:4150')
    
    logger.debug('Wiring event handlers...')
    
    @cb_reader.on_message.connect
    def call_blacklist_handler(reader, message):
        number = message.body.split(':')[0]
        if len(a) == 10: number = '1' + number # canonicalize 10 digit number into 1 + 10digits
        logger.info('Blacklisting ' + number + '...')
    
        backend_lock.acquire()
        backend_conn.send('B' + number)
        backend_lock.release()
    
    @cw_reader.on_message.connect
    def call_whitelist_handler(reader, message):
        number = message.body.split(':')[0]
        if len(a) == 10: number = '1' + number
        logger.info('Whitelisting ' + number + '...')
    
        backend_lock.acquire()
        backend_conn.send('W' + number)
        backend_lock.release()

    @hg_reader.on_message.connect
    def history_get_handler(reader, message):
        logger.warning('Call history handler stubbed out! Message: ' + message.body)
    
    @sr_reader.on_message.connect
    def settings_request_handler(reader, message):
        logger.warning('Settings request stubbed out! Message: ' + message.body)

    @sg_reader.on_message.connect
    def setting_get_handler(reader, message):
        logger.warning('Setting get request stubbed out! Message: ' + message.body)
    
    @ss_reader.on_message.connect
    def setting_set_handler(reader, message):
        logger.warning('Setting set request stubbed out! Message: ' + message.body)
    
    logger.debug('Starting readers...')
    cb_reader.start(block=False)
    cw_reader.start(block=False)
    hg_reader.start(block=False)
    sr_reader.start(block=False)
    sg_reader.start(block=False)
    ss_reader.start() # keep the process running by blocking