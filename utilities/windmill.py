#!/usr/bin/python2.5
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Windmill command line.

A separate script is used because windmill uses Python 2.5 features.
So it must be run separately.
"""
import _pythonpath
from windmill.bin.windmill_bin import main

if __name__ == '__main__':
    main()
