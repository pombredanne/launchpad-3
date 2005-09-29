
import os
import time
import canonical.lp

def getDBHost():
    # We must look for the PGHOST env var because we'll use it for mktap. If
    # we used it only to create connections we wouldn't need to use it,
    # because it's always used by any module that uses libpq.
    if os.environ.get('PGHOST'):
        dbhost = os.environ.get('PGHOST')
    elif canonical.lp.dbhost:
        dbhost = canonical.lp.dbhost
    else:
        dbhost = 'localhost'

    return dbhost

def wait_until_proxy_is_ready():
    start = time.time()
    delay = 0.05
    while time.time() - start < 5:  # loop for a maximum of 5 seconds
        try:
            if 'Starting factory' in open('twistd.log').read():
                return
        except IOError:
            pass
        time.sleep(delay)
        delay = delay * 2
    raise RuntimeError('Proxy not ready')

def wait_until_proxy_is_stopped():
    start = time.time()
    delay = 0.05
    while time.time() - start < 5:  # loop for a maximum of 5 seconds
        if not os.path.exists('twistd.pid'):
            return
        time.sleep(delay)
        delay = delay * 2
    raise RuntimeError('Proxy would not stop')
