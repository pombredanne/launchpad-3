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

twistd_script = os.path.abspath(os.path.join(
    os.path.dirname(__file__), 'sourcecode', 'twisted', 'bin', 'twistd'))


class TacFile(object):

    def __init__(self, name, tac_filename, configuration):
        """Create a TacFile object.

        :param name: A short name for the service. Used to name the pid file.
        :param tac_filename: The location of the TAC file, relative to this
            script.
        :param configuration: A config object with launch, logfile and spew
            attributes.
        """
        self.name = name
        self.tac_filename = tac_filename
        self.config = configuration

    def launch(self):
        # Imported here as path is not set fully on module load
        from canonical.pidfile import make_pidfile, pidfile_path

        # Don't run the server if it wasn't asked for. We only want it started
        # up developer boxes really, as the production server doesn't use this
        # startup script.
        if not self.config.launch:
            return

        pidfile = pidfile_path(self.name)
        logfile = self.config.logfile
        tacfile = os.path.abspath(os.path.join(
            os.path.dirname(__file__), self.tac_filename))

        args = [
            sys.executable,
            twistd_script,
            "--no_save",
            "--nodaemon",
            "--python", tacfile,
            "--pidfile", pidfile,
            "--prefix", self.name.capitalize(),
            "--logfile", logfile,
            ]

        if self.config.spew:
            args.append("--spew")

        # Note that startup tracebacks and evil programmers using 'print' will
        # cause output to our stdout. However, we don't want to have twisted
        # log to stdout and redirect it ourselves because we then lose the
        # ability to cycle the log files by sending a signal to the twisted
        # process.
        process = subprocess.Popen(args, stdin=subprocess.PIPE)
        process.stdin.close()
        # I've left this off - we still check at termination and we can
        # avoid the startup delay. -- StuartBishop 20050525
        #time.sleep(1)
        #if process.poll() != None:
        #    raise RuntimeError(
        #        "%s did not start: %d"
        #        % (self.name, process.returncode))
        def stop_process():
            if process.poll() is None:
                os.kill(process.pid, signal.SIGTERM)
                process.wait()
        atexit.register(stop_process)


def start_librarian():
    # Imported here as path is not set fully on module load
    from canonical.config import config

    # Don't run the Librarian if it wasn't asked for. We only want it
    # started up developer boxes really, as the production Librarian
    # doesn't use this startup script.
    if not config.librarian.server.launch:
        return

    if not os.path.isdir(config.librarian.server.root):
        os.makedirs(config.librarian.server.root, 0700)

    librarian = TacFile(
        'librarian', 'daemons/librarian.tac', config.librarian.server)
    librarian.launch()


def start_buildsequencer():
    # Imported here as path is not set fully on module load
    from canonical.config import config

    # Don't run the sequencer if it wasn't asked for. We only want it
    # started up developer boxes and dogfood really, as the production
    # sequencer doesn't use this startup script.
    if not config.buildsequencer.launch:
        return

    buildsequencer = TacFile('buildsequencer', 'daemons/buildd-sequencer.tac',
                             config.librarian.server)
    buildsequencer.launch()


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
    start_buildsequencer()

    # Store our process id somewhere
    make_pidfile('launchpad')

    main(argv[1:])


if __name__ == '__main__':
    run()
