# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0603

__metaclass__ = type
__all__ = ['start_launchpad']


import os
import sys
import atexit
import signal
import subprocess

from canonical.config import config
from canonical.pidfile import make_pidfile, pidfile_path
from zope.app.server.main import main
from canonical.launchpad.mailman import runmailman
from canonical.launchpad.testing import googletestservice

TWISTD_SCRIPT = None


def make_abspath(path):
    return os.path.abspath(os.path.join(config.root, *path.split('/')))


class Service(object):
    @property
    def should_launch(self):
        """Return true if this service should be launched."""
        return False

    def launch(self):
        """Launch the service, but do not block."""
        raise NotImplementedError


class TacFile(Service):

    def __init__(self, name, tac_filename, configuration, pre_launch=None):
        """Create a TacFile object.

        :param name: A short name for the service. Used to name the pid file.
        :param tac_filename: The location of the TAC file, relative to this
            script.
        :param configuration: A config object with launch, logfile and spew
            attributes.
        :param pre_launch: A callable that is called before the launch process.
        """
        # No point calling super's __init__.
        # pylint: disable-msg=W0231
        self.name = name
        self.tac_filename = tac_filename
        self.config = configuration
        if pre_launch is None:
            self.pre_launch = lambda: None
        else:
            self.pre_launch = pre_launch

    @property
    def should_launch(self):
        return self.config is not None and self.config.launch

    @property
    def logfile(self):
        """Return the log file to use.

        Default to the value of the configuration key logfile.
        """
        return self.config.logfile

    def launch(self):
        # Don't run the server if it wasn't asked for.
        if not self.should_launch:
            return

        self.pre_launch()

        pidfile = pidfile_path(self.name)
        logfile = self.config.logfile
        tacfile = make_abspath(self.tac_filename)

        args = [
            sys.executable,
            TWISTD_SCRIPT,
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
        stop_at_exit(process)


class RestrictedLibrarianService(TacFile):
    """Custom TacFile launcher for the restricted librarian."""
    def __init__(self):
        super(RestrictedLibrarianService, self).__init__(
            "restricted-librarian", "daemons/librarian.tac",
            config.librarian_server, prepare_for_librarian)

    def launch(self):
        """We need to set an environment variable to launch this service."""
        os.environ['RESTRICTED_LIBRARIAN'] = '1'
        try:
            super(RestrictedLibrarianService, self).launch()
        finally:
            del os.environ['RESTRICTED_LIBRARIAN']

    @property
    def logfile(self):
        return self.config.restricted_logfile


class MailmanService(Service):
    @property
    def should_launch(self):
        return config.mailman.launch

    def launch(self):
        # Don't run the server if it wasn't asked for.  Also, don't attempt to
        # shut it down at exit.
        if self.should_launch:
            runmailman.start_mailman()
            atexit.register(runmailman.stop_mailman)


class CodebrowseService(Service):
    @property
    def should_launch(self):
        return False

    def launch(self):
        process = subprocess.Popen(
            ['make', '-C', 'sourcecode/launchpad-loggerhead', 'fg'],
            stdin=subprocess.PIPE)
        process.stdin.close()
        stop_at_exit(process)

class GoogleWebService(Service):
    @property
    def should_launch(self):
        return config.google_test_service.launch

    def launch(self):
        process = googletestservice.start_as_process()
        stop_at_exit(process)


def stop_at_exit(process):
    """Create and register an atexit hook for killing a process.

    `process' is an instance of subprocess.Popen.
    """
    def stop_process():
        if process.poll() is None:
            os.kill(process.pid, signal.SIGTERM)
            process.wait()
    atexit.register(stop_process)

def prepare_for_librarian():
    if not os.path.isdir(config.librarian_server.root):
        os.makedirs(config.librarian_server.root, 0700)


SERVICES = {
    'librarian': TacFile('librarian', 'daemons/librarian.tac',
                         config.librarian_server, prepare_for_librarian),
    'restricted-librarian': RestrictedLibrarianService(),
    'buildsequencer': TacFile('buildsequencer',
                              'daemons/buildd-sequencer.tac',
                              config.buildsequencer),
    'authserver': TacFile('authserver', 'daemons/authserver.tac',
                          config.authserver),
    'sftp': TacFile('sftp', 'daemons/sftp.tac', config.codehosting),
    'mailman': MailmanService(),
    'codebrowse': CodebrowseService(),
    'google-webservice': GoogleWebService(),
    }


def make_css_slimmer():
    import contrib.slimmer
    inputfile = make_abspath(
        'lib/canonical/launchpad/icing/style.css')
    outputfile = make_abspath(
        'lib/canonical/launchpad/icing/+style-slimmer.css')

    cssdata = open(inputfile, 'rb').read()
    slimmed = contrib.slimmer.slimmer(cssdata, 'css')
    open(outputfile, 'w').write(slimmed)


def get_services_to_run(requested_services):
    """Return a list of services (TacFiles) given a list of service names.

    If no names are given, then the list of services to run comes from the
    launchpad configuration.

    If names are given, then only run the services matching those names.
    """
    if len(requested_services) == 0:
        return [svc for svc in SERVICES.values() if svc.should_launch]
    return [SERVICES[name] for name in requested_services]


def split_out_runlaunchpad_arguments(args):
    """Split the given command-line arguments into services to start and Zope
    arguments.

    The runlaunchpad script can take an optional '-r services,...' argument. If
    this argument is present, then the value is returned as the first element
    of the return tuple. The rest of the arguments are returned as the second
    element of the return tuple.

    Returns a tuple of the form ([service_name, ...], remaining_argv).
    """
    if len(args) > 1 and args[0] == '-r':
        return args[1].split(','), args[2:]
    return [], args


def start_launchpad(argv=list(sys.argv)):
    global TWISTD_SCRIPT
    TWISTD_SCRIPT = make_abspath('sourcecode/twisted/bin/twistd')

    # We really want to replace this with a generic startup harness.
    # However, this should last us until this is developed
    services, argv = split_out_runlaunchpad_arguments(argv[1:])
    services = get_services_to_run(services)
    for service in services:
        service.launch()

    # Store our process id somewhere
    make_pidfile('launchpad')

    # Create a new compressed +style-slimmer.css from style.css in +icing.
    make_css_slimmer()
    main(argv)
