import gnsq
import logging
import multiprocessing
import settings

backend_conn = None
backend_lock = None

# TODO: refactor more of the message parsing logic out of executive and into here

def handler_process(pipe):
    global backend_conn, backend_lock
    backend_conn = pipe
    backend_lock = multiprocessing.Lock()
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    logger.debug('Establishing subscriptions to NSQ topics...')
    logging.getLogger('gnsq').setLevel(logging.INFO)
    
    cb_reader = gnsq.Reader('call_blacklist', 'backend_py', '127.0.0.1:4150')
    br_reader = gnsq.Reader('blacklist_remove', 'backend_py', '127.0.0.1:4150')
    cw_reader = gnsq.Reader('call_whitelist', 'backend_py', '127.0.0.1:4150')
    hg_reader = gnsq.Reader('history_get', 'backend_py', '127.0.0.1:4150')
    bg_reader = gnsq.Reader('blacklist_get', 'backend_py', '127.0.0.1:4150')
    sr_reader = gnsq.Reader('settings_request_all', 'backend_py', '127.0.0.1:4150')
    sg_reader = gnsq.Reader('setting_get', 'backend_py', '127.0.0.1:4150')
    ss_reader = gnsq.Reader('setting_set', 'backend_py', '127.0.0.1:4150')
    
    logger.debug('Wiring event handlers...')
    
    @cb_reader.on_message.connect
    def call_blacklist_handler(reader, message):
        # received message: number:name
        number = message.body.split(':')[0]
        logger.info('Blacklisting ' + number + '...')
    
        backend_lock.acquire()
        backend_conn.send(['blacklist', number])
        backend_lock.release()
    
    @br_reader.on_message.connect
    def blacklist_remove_handler(reader, message):
        # received message: number
        number = message.body
        logger.info('Removing ' + number + ' from blacklist...')
    
        backend_lock.acquire()
        backend_conn.send(['blacklist_remove', number])
        backend_lock.release()
    
    @cw_reader.on_message.connect
    def call_whitelist_handler(reader, message):
        # received message: number:name
        number = message.body.split(':')[0]
        logger.info('Whitelisting ' + number + '...')
    
        backend_lock.acquire()
        backend_conn.send(['whitelist', number])
        backend_lock.release()

    @hg_reader.on_message.connect
    def history_get_handler(reader, message):
        params = message.body.split(':')
        backend_lock.acquire()
        backend_conn.send(['history', params])
        backend_lock.release()
    
    @bg_reader.on_message.connect
    def blacklist_get_handler(reader, message):
        params = message.body.split(':')
        backend_lock.acquire()
        backend_conn.send(['blacklist_get', params])
        backend_lock.release()
    
    # request for all settings
    @sr_reader.on_message.connect
    def settings_request_handler(reader, message):
        backend_lock.acquire()
        backend_conn.send(['settings_request'])
        backend_lock.release()
    
    # request to get one setting
    @sg_reader.on_message.connect
    def setting_get_handler(reader, message):
        backend_lock.acquire()
        backend_conn.send(['setting_get', message.body])
        backend_lock.release()
    
    # request to set one setting
    @ss_reader.on_message.connect
    def setting_set_handler(reader, message):
        backend_lock.acquire()
        alteredSetting = message.body.split(':')
        backend_conn.send(['setting_set', alteredSetting[0], alteredSetting[1]]) # setting, new state
        backend_lock.release()
    
    logger.debug('Starting readers...')
    cb_reader.start(block=False)
    br_reader.start(block=False)
    cw_reader.start(block=False)
    hg_reader.start(block=False)
    bg_reader.start(block=False)
    sr_reader.start(block=False)
    sg_reader.start(block=False)
    ss_reader.start() # keep the process running by blocking
