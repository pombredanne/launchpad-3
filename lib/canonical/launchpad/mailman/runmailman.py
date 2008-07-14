# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Start and stop the Mailman processes."""

__metaclass__ = type
__all__ = [
    'start_mailman',
    'stop_mailman',
    ]


import os
import sys
import subprocess

import canonical
from canonical.launchpad.mailman.config import configure_prefix
from canonical.launchpad.mailman.monkeypatches import monkey_patch


def mailmanctl(command, quiet=False, config=None):
    """Run mailmanctl command.

    :param command: the command to use.
    :param quiet: when this is true, no output will happen unless, an error
        happens.
    :param config: The CanonicalConfig object to take configuration from.
        Defaults to the global one.
    :raises RuntimeError: when quiet is True and the command failed.
    """
    if config is None:
        config = canonical.config.config
    mailman_path = configure_prefix(config.mailman.build_prefix)
    mailman_bin  = os.path.join(mailman_path, 'bin')
    args = ['./mailmanctl', 'stop']
    if quiet:
        stdout=subprocess.PIPE
        stderr=subprocess.STDOUT
    else:
        stdout=None
        stderr=None
    env = dict(os.environ)
    env['LPCONFIG'] = config.instance_name
    mailmanctl = subprocess.Popen(
        args, cwd=mailman_bin, stdout=stdout, stderr=stderr, env=env)
    code = mailmanctl.wait()
    if code:
        if quiet:
            raise RuntimeError(
                'mailmanctl %s failed: %d\n%s' % (
                    command, code, mailmanctl.stdout.read()))
        else:
            print >>sys.stderr, 'mailmanctl %s failed: %d' % (command, code)


def stop_mailman(quiet=False, config=None):
    """Alias for mailmanctl('stop')."""
    mailmanctl('stop', quiet=quiet, config=config)


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
    mailmanctl('start', quiet=quiet, config=config)
