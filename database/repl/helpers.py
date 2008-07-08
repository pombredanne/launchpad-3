# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Common helpers for replication scripts."""

import subprocess
import sys

__metaclass__ = type
__all__ = []


def execute_slonik(script):
    """Use the slonik command line tool to run a slonik script.

    :param script: The script as a string. Preamble should not be included.
    """
    slonik_process = subprocess.Popen(
            ['slonik'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    script = preamble() + script

    (out, err) = slonik_process.communicate(script)

    if slonik_process.returncode != 0:
        print >> sys.stderr, "slonik failed to complete:"
        print >> sys.stderr, out
        sys.exit(1)

    print out


def execute_sql(script):
    """Use the slonik command line tool to run a SQL script.

    :param sql_script: The script as a string.
    """
    raise NotImplementedError


def preamble():
    """Return the preable needed at the start of all slonik scripts."""
    # This is just a place holder. We need to generate or select a
    # preamble based on LPCONFIG. Or better yet, pull it from the master
    # database if we are not initializing the cluster.
    return "include <preamble.sk>;\n"
