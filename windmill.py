#!/usr/bin/python2.5
"""Windmill wrapper script.

Note: Windmill requires Python 2.5
"""
import os
import sys

here = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(here, 'lib'))

# Set PYTHONPATH environment variable for spawned processes
os.environ['PYTHONPATH'] = ':'.join(sys.path)

from windmill.bin.windmill_bin import main

if __name__ == '__main__':
    main()
