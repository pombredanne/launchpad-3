#! /usr/bin/python2.4
##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Start script for Launchpad: loads configuration and starts the server.

Usage: runlaunchpad.py [-r librarian,sftp,authserver,buildsequencer] [<zope args>]

$Id: z3.py 25266 2004-06-04 21:25:45Z jim $
"""

import os
import sys

if sys.version_info < (2, 4, 0):
    print ("ERROR: Your python version is not supported by Launchpad."
            "Launchpad needs Python 2.4 or greater. You are running: " 
            + sys.version)
    sys.exit(1)

from configs import generate_overrides


def set_up_sys_path(program):
    basepath = filter(None, sys.path)
    src = 'lib'
    here = os.path.dirname(os.path.abspath(program))
    srcdir = os.path.join(here, src)
    sys.path = [srcdir, here] + basepath


def run(argv=list(sys.argv)):
    # Sort ZCML overrides for our current config
    generate_overrides()

    # setting python paths
    program = argv[0]
    set_up_sys_path(program)

    # Import canonical modules here, after path munging
    from canonical.launchpad.scripts.runlaunchpad import start_launchpad

    start_launchpad(argv)


if __name__ == '__main__':
    run()
