# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Start script for Launchpad: loads configuration and starts the server."""

__metaclass__ = type
__all__ = ['start_launchpad']


import sys
import os
import os.path
import atexit
import signal
import subprocess
import time
from zope.app.server.main import main

from canonical.pidfile import make_pidfile, pidfile_path


ROCKETFUEL_ROOT = None


def make_abspath(path):
    return os.path.abspath(os.path.join(ROCKETFUEL_ROOT, *path.split('/')))


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

        # Don't run the server if it wasn't asked for. 
        if not self.config.launch:
            return

        twistd_script = make_abspath('sourcecode/twisted/bin/twistd')
        pidfile = pidfile_path(self.name)
        logfile = self.config.logfile
        tacfile = make_abspath(self.tac_filename)

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

    # Don't run the Librarian if it wasn't asked for. Although launch() guards
    # against this, we also need to make sure that the Librarian directories
    # are not created if we are not running the Librarian.
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

    buildsequencer = TacFile('buildsequencer', 'daemons/buildd-sequencer.tac',
                             config.buildsequencer)
    buildsequencer.launch()


def start_authserver():
    # Imported here as path is not set fully on module load
    from canonical.config import config

    authserver = TacFile(
        'authserver', 'daemons/authserver.tac', config.authserver)
    authserver.launch()


def start_supermirrorsftp():
    # Imported here as path is not set fully on module load
    from canonical.config import config

    sftp = TacFile('sftp', 'daemons/sftp.tac', config.supermirrorsftp)
    sftp.launch()


def make_css_slimmer():
    import contrib.slimmer
    inputfile = make_abspath(
        'lib/canonical/launchpad/icing/style.css')
    outputfile = make_abspath(
        'lib/canonical/launchpad/icing/+style-slimmer.css')

    cssdata = open(inputfile, 'rb').read()
    slimmed = contrib.slimmer.slimmer(cssdata, 'css')
    open(outputfile, 'w').write(slimmed)


def start_launchpad(argv=list(sys.argv)):
    global ROCKETFUEL_ROOT
    ROCKETFUEL_ROOT = os.path.dirname(os.path.abspath(argv[0]))

    # Disgusting hack to use our extended config file schema rather than the
    # Z3 one. TODO: Add command line options or other to Z3 to enable overriding
    # this -- StuartBishop 20050406
    from zdaemon.zdoptions import ZDOptions
    ZDOptions.schemafile = make_abspath('lib/canonical/config/schema.xml')


    # We really want to replace this with a generic startup harness.
    # However, this should last us until this is developed
    start_librarian()
    start_buildsequencer()
    start_authserver()
    start_supermirrorsftp()

    # Store our process id somewhere
    make_pidfile('launchpad')

    # Create a new compressed +style-slimmer.css from style.css in +icing.
    make_css_slimmer()
    main(argv[1:])

