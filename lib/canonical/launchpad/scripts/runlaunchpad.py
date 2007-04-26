# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['start_launchpad']


import os
import sys
import atexit
import random
import signal
import socket
import subprocess

from canonical.config import config
from canonical.pidfile import make_pidfile, pidfile_path
from string import ascii_letters, digits
from zope.app.server.main import main


ROCKETFUEL_ROOT = None
TWISTD_SCRIPT = None


def make_abspath(path):
    return os.path.abspath(os.path.join(ROCKETFUEL_ROOT, *path.split('/')))


def random_characters(length=10):
    empty_string = ''
    chars = digits + ascii_letters
    return empty_string.join(random.choice(chars) for c in range(length))


class Service(object):
    @property
    def shouldLaunch(self):
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
        self.name = name
        self.tac_filename = tac_filename
        self.config = configuration
        if pre_launch is None:
            self.pre_launch = lambda: None
        else:
            self.pre_launch = pre_launch

    @property
    def shouldLaunch(self):
        return self.config is not None and self.config.launch

    def launch(self):
        # Don't run the server if it wasn't asked for. 
        if not self.shouldLaunch:
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
        def stop_process():
            if process.poll() is None:
                os.kill(process.pid, signal.SIGTERM)
                process.wait()
        atexit.register(stop_process)


class MailmanService(Service):
    @property
    def shouldLaunch(self):
        return config.mailman.launch

    def launch(self):
        # Don't run the server if it wasn't asked for.
        if not self.shouldLaunch:
            return

        # Add the directory containing the Mailman package to our sys.path.
        if not config.mailman.build.prefix:
            mailman_path = make_abspath('lib/mailman')
        else:
            mailman_path = os.path.abspath(config.mailman.build.prefix)

        # We need the Mailman bin directory so we can run some of Mailman's
        # command line scripts.
        mailman_bin = os.path.join(mailman_path, 'bin')

        if config.mailman.build.host_name:
            hostname = config.mailman.build.host_name
        else:
            hostname = socket.getfqdn()

        # Monkey-patch the installed Mailman 2.1 tree.
        from canonical.mailman.monkeypatches import monkey_patch
        monkey_patch(mailman_path, config)

        # Ensure that the site list has been created.  We won't use this
        # operationally, but it's required by Mailman 2.1.  This is the
        # cheapest way to do this.  Throw away the actual output, since we
        # only care about the return code.
        sys.path.append(mailman_path)
        import Mailman.mm_cfg

        retcode = subprocess.call(
            ('./config_list', '-o', '/dev/null',
             Mailman.mm_cfg.MAILMAN_SITE_LIST),
            cwd=mailman_bin,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if retcode:
            if config.mailman.build.site_list_owner:
                addr, password = config.mailman.build.site_list_owner.split(
                                                                    ':', 1)
            else:
                localpart = random_characters()
                password  = random_characters()
                addr = localpart + '@example.com'

            # The site list does not yet exist, so create it now.
            retcode = subprocess.call(('./newlist', '--quiet',
                                       '--emailhost=' + hostname,
                                       Mailman.mm_cfg.MAILMAN_SITE_LIST,
                                       addr, password),
                                      cwd=mailman_bin)
            if retcode:
                print >> sys.stderr, 'Could not create site list'
                sys.exit(retcode)

        # Start the Mailman master qrunner.  If that succeeds, then set things
        # up so that it will be stopped when runlaunchpad.py exits.
        def stop_mailman():
            # Ignore any errors
            code = subprocess.call(('./mailmanctl', 'stop'), cwd=mailman_bin)
            if retcode:
                print >> sys.stderr, 'mailmanctl did not stop cleanly:', code
                # There's no point in calling sys.exit() since we're already
                # exiting!

        code = subprocess.call(('./mailmanctl', 'start'), cwd=mailman_bin)
        if code:
            print >> sys.stderr, 'mailmanctl did not start cleanly'
            sys.exit(code)
        atexit.register(stop_mailman)


def prepare_for_librarian():
    if not os.path.isdir(config.librarian.server.root):
        os.makedirs(config.librarian.server.root, 0700)


SERVICES = {
    'librarian': TacFile('librarian', 'daemons/librarian.tac',
                         config.librarian.server, prepare_for_librarian),
    'buildsequencer': TacFile('buildsequencer', 'daemons/buildd-sequencer.tac',
                              config.buildsequencer),
    'authserver': TacFile('authserver', 'daemons/authserver.tac',
                          config.authserver),
    'sftp': TacFile('sftp', 'daemons/sftp.tac', config.supermirrorsftp),
    'mailman': MailmanService(),
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
    """Return a list of services (i.e. TacFiles) given a list of service names.

    If no names are given, then the list of services to run comes from the
    launchpad configuration.

    If names are given, then only run the services matching those names.
    """
    if len(requested_services) == 0:
        return [svc for svc in SERVICES.values() if svc.shouldLaunch]
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
    global ROCKETFUEL_ROOT, TWISTD_SCRIPT
    ROCKETFUEL_ROOT = os.path.dirname(os.path.abspath(argv[0]))
    TWISTD_SCRIPT = make_abspath('sourcecode/twisted/bin/twistd')

    # Disgusting hack to use our extended config file schema rather than the
    # Z3 one. TODO: Add command line options or other to Z3 to enable
    # overriding this -- StuartBishop 20050406
    from zdaemon.zdoptions import ZDOptions
    ZDOptions.schemafile = make_abspath('lib/canonical/config/schema.xml')

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
