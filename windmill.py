#!/usr/bin/python2.5
"""Windmill wrapper script.

Windmill requires Python 2.5
"""
import os
import sys

if os.getsid(0) == os.getsid(os.getppid()):
    # We need to become the process group leader so test_on_merge.py
    # can reap its children.
    #
    # Note that if setpgrp() is used to move a process from one
    # process group to another (as is done by some shells when
    # creating pipelines), then both process groups must be part of
    # the same session.
    os.setpgrp()

# Enable Storm's C extensions
os.environ['STORM_CEXTENSIONS'] = '1'

here = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(here, 'lib'))

# Set PYTHONPATH environment variable for spawned processes
os.environ['PYTHONPATH'] = ':'.join(sys.path)

from windmill.bin.windmill_bin import main

if __name__ == '__main__':
    main()
