# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Useful utilities."""

__metaclass__ = type

__all__ = [
    'fail',
    'log',
    'run',
    'spew',
    ]


import sys
import subprocess


SPACE = ' '


def fail(message, *args):
    print >> sys.stderr, 'FAIL:', message % args
    sys.exit(1)


def log(message, *args):
    print >> sys.stderr, message % args


def spew(message, *args):
    log(message, *args)


def run(*args):
    proc = subprocess.Popen(args)
    if proc.wait() != 0:
        if proc.stderr:
            log(proc.stderr)
        fail('[%d] %s', proc.returncode, SPACE.join(args))
