#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Build Jobs initialization."""

__metaclass__ = type

import _pythonpath

from canonical.config import config
from lp.soyuz.scripts.buildd import QueueBuilder

if __name__ == '__main__':
    script = QueueBuilder('queue-builder', dbuser=config.builddmaster.dbuser)
    script.lock_or_quit()
    try:
        script.run()
    finally:
        script.unlock()
