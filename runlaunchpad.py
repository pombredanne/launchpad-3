#! /usr/bin/env python2.4
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
import sys

if sys.version_info < (2, 4, 0):
    print ("ERROR: Your python version is not supported by Launchpad."
            "Launchpad needs Python 2.4 or greater. You are running: " 
            + sys.version)
    sys.exit(1)

import os
import os.path
import atexit
import signal
import subprocess
import time
from zope.app.server.main import main
from configs import generate_overrides

basepath = filter(None, sys.path)

# Disgusting hack to use our extended config file schema rather than the
# Z3 one. TODO: Add command line options or other to Z3 to enable overriding
# this -- StuartBishop 20050406
from zdaemon.zdoptions import ZDOptions
ZDOptions.schemafile = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'lib', 'canonical',
        'config', 'schema.xml'))

def start_librarian():
    # Imported here as path is not set fully on module load
    from canonical.config import config
    from canonical.pidfile import make_pidfile, pidfile_path

    # Don't run the Librarian if it wasn't asked for. We only want it
    # started up developer boxes really, as the production Librarian
    # doesn't use this startup script.
    if not config.librarian.server.launch:
        return

    if not os.path.isdir(config.librarian.server.root):
        os.makedirs(config.librarian.server.root, 0700)

    pidfile = pidfile_path('librarian')
    tacfile = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'daemons', 'librarian.tac'
        ))

    ver = '%d.%d' % sys.version_info[:2]
    args = [
        "twistd%s" % ver,
        "--no_save",
        "--nodaemon",
        "--python", tacfile,
        "--pidfile", pidfile,
        "--logfile", "-",
        "--prefix", "Librarian",
        ]

    if config.librarian.server.spew:
        args.append("--spew")

    librarian_process = subprocess.Popen(args, stdin=subprocess.PIPE)
    librarian_process.stdin.close()
    # I've left this off - we still check at termination and we can
    # avoid the startup delay. -- StuartBishop 20050525
    #time.sleep(1)
    #if librarian_process.poll() != None:
    #    raise RuntimeError(
    #            "Librarian did not start: %d" % librarian_process.returncode
    #            )
    def stop_librarian():
        if librarian_process.poll() is None:
            os.kill(librarian_process.pid, signal.SIGTERM)
            librarian_process.wait()
    atexit.register(stop_librarian)


def run(argv=list(sys.argv)):

    # Sort ZCML overrides for our current config
    generate_overrides()

    # setting python paths
    program = argv[0]

    src = 'lib'
    here = os.path.dirname(os.path.abspath(program))
    srcdir = os.path.join(here, src)
    sys.path = [srcdir, here] + basepath

    # Import canonical modules here, after path munging
    from canonical.pidfile import make_pidfile, pidfile_path

    # We really want to replace this with a generic startup harness.
    # However, this should last us until this is developed
    start_librarian()

    # Store our process id somewhere
    make_pidfile('launchpad')

    main(argv[1:])
        

if __name__ == '__main__':
    run()
