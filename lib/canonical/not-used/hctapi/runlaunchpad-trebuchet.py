# Copyright 2005 Canonical Ltd.  All rights reserved.

# NOTE: This code was taken out of runlaunchpad.py. It was used to start the
# trebuchet daemon, however this daemon has been superseded by the generic
# Launchpad xmlrpc server. -- David Allouche 2006-09-25

import atexit
import os
import signal
import subprocess
import sys


def start_trebuchet():
    # Imported here as path is not set fully on module load
    from canonical.config import config
    from canonical.pidfile import make_pidfile, pidfile_path

    # Don't run the Trebuchet if it wasn't asked for.
    if not config.trebuchet.server.launch:
        return

    if not os.path.isdir(config.trebuchet.server.root):
        os.makedirs(config.trebuchet.server.root, 0700)

    pidfile = pidfile_path('trebuchet')
    logfile = config.trebuchet.server.logfile
    tacfile = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'daemons', 'trebuchet.tac'
        ))

    ver = '%d.%d' % sys.version_info[:2]
    args = [
        "twistd%s" % ver,
        "--no_save",
        "--nodaemon",
        "--python", tacfile,
        "--pidfile", pidfile,
        "--prefix", "Trebuchet",
        "--logfile", logfile,
        ]

    if config.trebuchet.server.spew:
        args.append("--spew")

    trebuchet_process = subprocess.Popen(args, stdin=subprocess.PIPE)
    trebuchet_process.stdin.close()
    # I've left this off - we still check at termination and we can
    # avoid the startup delay. -- StuartBishop 20050525
    #time.sleep(1)
    #if trebuchet_process.poll() != None:
    #    raise RuntimeError(
    #            "Trebuchet did not start: %d" % trebuchet_process.returncode
    #            )
    def stop_trebuchet():
        if trebuchet_process.poll() is None:
            os.kill(trebuchet_process.pid, signal.SIGTERM)
            trebuchet_process.wait()
        else:
            print >> sys.stderr, "*** ERROR: Trebuchet died prematurely!"
            print >> sys.stderr, "***        Return code was %d" % (
                    trebuchet_process.returncode,
                    )
    atexit.register(stop_trebuchet)





