# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper for test_siguser2.py."""

import logging
import signal
import sys
import time

from ZConfig.components.logger.loghandler import FileHandler

from canonical.launchpad.webapp.sigusr2 import setup_sigusr2

counter = 1

def sigusr1_handler(signum, frame):
    """Emit a message"""
    global counter
    logging.getLogger('').error('Message %d' % counter)
    counter += 1

if __name__ == '__main__':
    logging.getLogger('').addHandler(FileHandler(sys.argv[1]))
    signal.signal(signal.SIGUSR1, sigusr1_handler)
    setup_sigusr2(None)
    while True:
        if counter > 2:
            sys.exit(0)
        time.sleep(0.01)
