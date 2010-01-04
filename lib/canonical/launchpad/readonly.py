# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helpers for running Launchpad in read-only mode.

To switch an app server to read-only mode, all you need to do is create a file
named read-only.txt under the root of the Launchpad tree and emit a SIGUSR2
signal.
"""

# XXX: Having two switches (the read-only.txt and the SIGUSR2) to turn on
# read-only doesn't sound like a very good idea to me, so we may want to use
# just SIGUSR2 to create a read-only.txt file and trigger the code that sets
# the configs with the appropriate values.  Similarly, when starting up we'd
# check for the presence of read-only.txt and set the config variables
# with the appropriate values.  That means we can't use SIGUSR2 to switch back
# to read-write mode, though.

import os


def is_read_only():
    root = os.path.join(
        os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)
    return os.path.isfile(os.path.join(root, 'read-only.txt'))
