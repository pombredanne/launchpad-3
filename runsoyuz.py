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
# arch-tag: 65bbad4c-38de-4a86-9aa5-d4d2fd38c97d
"""Start script for Soyuz: loads configuration and starts the server.

$Id: z3.py 25266 2004-06-04 21:25:45Z jim $
"""
import os
import sys

basepath = filter(None, sys.path)

def run(argv=list(sys.argv)):

    if sys.version_info < ( 2,3,4 ):
        print """\
        ERROR: Your python version is not supported by Zope3.
        Zope3 needs Python 2.3.4 or greater. You are running:""" + sys.version
        sys.exit(1)

    # Refuse to run without principals.zcml
    if not os.path.exists('principals.zcml'):
        print """\
        ERROR: You need to create principals.zcml

        The file principals.zcml contains your "bootstrap" user
        database. You aren't going to get very far without it.  Start
        by copying sample_principals.zcml and then modify the
        example principal and role settings.
        """
        sys.exit(1)

    # setting python paths
    program = argv[0]

    src = 'lib'
    here = os.path.dirname(os.path.abspath(program))
    srcdir = os.path.abspath(src)
    sys.path = [srcdir, here] + basepath

    from zope.app.server.main import main
    main(argv[1:])


if __name__ == '__main__':
    run()
