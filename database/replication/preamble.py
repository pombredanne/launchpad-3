#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Generate a preamble for slonik(1) scripts based on the current LPCONFIG.
"""

__metaclass__ = type
__all__ = []

import _pythonpath

import os
import time

import replication.helpers

if __name__ == '__main__':
    print '# slonik(1) preamble generated %s' % time.ctime()
    print '# LPCONFIG=%s' % (os.environ.get('LPCONFIG', None),)
    print
    print replication.helpers.preamble()

