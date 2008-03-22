# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import tempfile
import os
import atexit
import sys
from signal import signal, SIGTERM

from canonical.config import config

def pidfile_path(service_name):
    """Return the full pidfile path for the given service

    >>> pidfile_path('nuts') == '/tmp/%s-nuts.pid' % config.instance_name
    True
    """
    return os.path.join(config.pid_dir, '%s-%s.pid' % (
        config.instance_name, service_name
        ))


def make_pidfile(service_name):
    """Write the current process id to a PID file.

    Also installs an atexit handler to remove the file on process termination.

    Also installs a SIGTERM signal handler to remove the file on SIGTERM.
    If you install your own handler, you will want to call remove_pidfile
    inside it.

    To test, we run a subprocess that creates a pidfile and checks
    that the correct PID is stored in it.

    >>> cmd = '''
    ... import os.path, sys
    ... from canonical.pidfile import make_pidfile, pidfile_path
    ... make_pidfile('nuts')
    ... sys.exit(
    ...     int(open(pidfile_path('nuts')).read().strip() == str(os.getpid()))
    ...     )
    ... '''
    >>> import sys, subprocess
    >>> cmd = '%s -c "%s"' % (sys.executable, cmd)
    >>> subprocess.call(cmd, shell=True)
    1

    Make sure that the process has been removed.

    >>> os.path.exists(pidfile_path('nuts'))
    False

    And we want the pidfile to be removed if the process is exited with
    Ctrl-C or SIGTERM, too.

    >>> from signal import SIGINT, SIGTERM
    >>> import time
    >>> for signal in [SIGINT, SIGTERM]:
    ...     cmd = '''
    ... from canonical.pidfile import make_pidfile
    ... import time
    ... make_pidfile('nuts')
    ... try:
    ...     time.sleep(30)
    ... except KeyboardInterrupt:
    ...     pass'''
    ...     cmd = '%s -c "%s"' % (sys.executable, cmd)
    ...     p = subprocess.Popen(cmd, shell=True)
    ...     count = 0
    ...     while not os.path.exists(pidfile_path('nuts')) and count < 100:
    ...         time.sleep(0.1)
    ...         count += 1
    ...     os.kill(int(open(pidfile_path('nuts')).read()), SIGINT)
    ...     time.sleep(2)
    ...     print os.path.exists(pidfile_path('nuts'))
    False
    False

    """
    pidfile = pidfile_path(service_name)
    if os.path.exists(pidfile):
        raise RuntimeError("PID file %s already exists. Already running?" %
                pidfile)

    atexit.register(remove_pidfile, service_name)
    def remove_pidfile_handler(*ignored):
        sys.exit(-1 * SIGTERM)
    signal(SIGTERM, remove_pidfile_handler)

    fd, tempname = tempfile.mkstemp(dir=os.path.dirname(pidfile))
    outf = os.fdopen(fd, 'w')
    outf.write(str(os.getpid())+'\n')
    outf.flush()
    outf.close()
    os.rename(tempname, pidfile)


def remove_pidfile(service_name):
    """Remove the PID file.

    This should only be needed if you are overriding the default SIGTERM
    signal handler.
    """
    pidfile = pidfile_path(service_name)
    if os.path.exists(pidfile):
        # Check that the PID is actually ours in case something overwrote
        # it or we are forked.
        pid = open(pidfile).read()
        try:
            pid = int(pid)
        except ValueError:
            raise ValueError("Invalid PID %s" % repr(pid))
        if pid == os.getpid():
            os.unlink(pidfile)


def get_pid(service_name):
    """Return the PID for the given service as an integer, or None

    May raise a ValueError if the PID file is corrupt.

    This method will only be needed by service or monitoring scripts.

    Currently no checking is done to ensure that the process is actually
    running, is healthy, or died horribly a while ago and its PID being
    used by something else. What we have is probably good enough.

    >>> get_pid('nuts') is None
    True
    >>> make_pidfile('nuts')
    >>> get_pid('nuts') == os.getpid()
    True
    >>> remove_pidfile('nuts')
    >>> get_pid('nuts') is None
    True
    """
    pidfile = pidfile_path(service_name)
    try:
        pid = open(pidfile).read()
        return int(pid)
    except IOError:
        return None
    except ValueError:
        raise ValueError("Invalid PID %s" % repr(pid))

