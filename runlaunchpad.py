#! /usr/bin/env python2.3
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

$Id: z3.py 25266 2004-06-04 21:25:45Z jim $
"""
import os
import sys
from zope.app.server.main import main

basepath = filter(None, sys.path)

# Disgusting hack to use our extended config file schema rather than the
# Z3 one. TODO: Add command line options or other to Z3 to enable overriding
# this -- StuartBishop 20050406
from zdaemon.zdoptions import ZDOptions
ZDOptions.schemafile = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'lib', 'canonical',
        'config', 'schema.xml'))

def run(argv=list(sys.argv)):

    if sys.version_info < ( 2,3,4 ):
        print """\
        ERROR: Your python version is not supported by Zope3.
        Zope3 needs Python 2.3.4 or greater. You are running:""" + sys.version
        sys.exit(1)

    # setting python paths
    program = argv[0]

    src = 'lib'
    here = os.path.dirname(os.path.abspath(program))
    srcdir = os.path.join(here, src)
    sys.path = [srcdir, here] + basepath

    main(argv[1:])


if __name__ == '__main__':
    run()
