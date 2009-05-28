# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Start and stop the Mailman processes."""

__metaclass__ = type
__all__ = [
    'start_mailman',
    'stop_mailman',
    ]


import os
import sys
import errno
import signal
import subprocess

import canonical
from canonical.launchpad.mailman.config import configure_prefix
from canonical.launchpad.mailman.monkeypatches import monkey_patch


def mailmanctl(command, quiet=False, config=None, *additional_arguments):
    """Run mailmanctl command.

    :param command: the command to use.
    :param quiet: when this is true, no output will happen unless, an error
        happens.
    :param config: The CanonicalConfig object to take configuration from.
        Defaults to the global one.
    :param additional_arguments: additional command arguments to pass to the
        mailmanctl program.
    :raises RuntimeError: when quiet is True and the command failed.
    """
    if config is None:
        config = canonical.config.config
    mailman_path = configure_prefix(config.mailman.build_prefix)
    mailman_bin  = os.path.join(mailman_path, 'bin')
    args = ['./mailmanctl']
    args.extend(additional_arguments)
    args.append(command)
    if quiet:
        stdout = subprocess.PIPE
        stderr = subprocess.STDOUT
    else:
        stdout = None
        stderr = None
    env = dict(os.environ)
    env['LPCONFIG'] = config.instance_name
    # We want to make sure that the Launchpad process will have the benefit of
    # all of the dependency paths inserted by the buildout bin/run script. We
    # pass them via PYTHONPATH.
    env['PYTHONPATH'] = os.path.pathsep.join(sys.path)
    process = subprocess.Popen(
        args, cwd=mailman_bin, stdout=stdout, stderr=stderr, env=env)
    code = process.wait()
    if code:
        if quiet:
            raise RuntimeError(
                'mailmanctl %s failed: %d\n%s' % (
                    command, code, process.stdout.read()))
        else:
            print >> sys.stderr, 'mailmanctl %s failed: %d' % (command, code)


def stop_mailman(quiet=False, config=None):
    """Alias for mailmanctl('stop')."""
    mailmanctl('stop', quiet, config)
    # Further, if the Mailman master pid file was not removed, then the
    # master watcher, and probably one of its queue runners, did not die.
    # Kill it hard and clean up after it.
    if config is None:
        config = canonical.config.config
    mailman_path = configure_prefix(config.mailman.build_prefix)
    master_pid_path = os.path.join(mailman_path, 'data', 'master-qrunner.pid')
    try:
        master_pid_file = open(master_pid_path)
    except IOError, error:
        if error.errno == errno.ENOENT:
            # It doesn't exist, so we're all done.
            return
        raise
    try:
        master_pid = int(master_pid_file.read().strip())
    finally:
        master_pid_file.close()
    try:
        # Kill the entire process group.
        os.kill(master_pid, -signal.SIGKILL)
    except OSError, error:
        if error.errno == errno.ESRCH:
            # The process does not exist.  It could be a zombie that has yet
            # to be waited on, but let's not worry about that.
            return
        raise
    try:
        os.remove(master_pid_path)
    except OSError, error:
        if error.errno != errno.ENOENT:
            raise
    lock_dir = os.path.join(mailman_path, 'locks')
    for filename in os.listdir(lock_dir):
        os.remove(os.path.join(lock_dir, filename))


def start_mailman(quiet=False, config=None):
    """Start the Mailman master qrunner.

    The client of start_mailman() is responsible for ensuring that
    stop_mailman() is called at the appropriate time.

    :param quiet: when this is true, no output will happen unless, an error
        happens.
    :param config: The CanonicalConfig object to take configuration from.
        Defaults to the global one.
    :raises RuntimeException: when Mailman fails to start successfully.
    """
    if config is None:
        config = canonical.config.config
    # We need the Mailman bin directory so we can run some of Mailman's
    # command line scripts.
    mailman_path = configure_prefix(config.mailman.build_prefix)
    mailman_bin  = os.path.join(mailman_path, 'bin')

    # Monkey-patch the installed Mailman 2.1 tree.
    monkey_patch(mailman_path, config)
    # Start Mailman.  Pass in the -s flag so that any stale master pid files
    # will get deleted.  "Stale" means the process that owned the pid no
    # longer exists, so this can't hurt anything.
    mailmanctl('start', quiet, config, '-s')
