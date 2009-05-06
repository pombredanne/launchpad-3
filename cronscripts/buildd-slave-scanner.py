#!/usr/bin/python2.4
# Copyright 2004 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>
#         Celso Providelo <celso.providelo@canonical.com>
#
# Builder Slave Scanner and result collector

__metaclass__ = type

import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.buildd import SlaveScanner


if __name__ == '__main__':
    script = SlaveScanner('slave-scanner', dbuser=config.builddmaster.dbuser)
    script.lock_or_quit()
    try:
        script.run()
    finally:
        script.unlock()

