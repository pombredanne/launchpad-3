# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Common helpers for replication scripts."""

import subprocess
import sys

from canonical.launchpad.scripts.logger import log

__metaclass__ = type
__all__ = []

def sync(timeout=60):
    """Generate a sync event and wait for it to complete on all nodes.
   
    This means that all pending events have propagated and are in sync
    to the point in time this method was called. This might take several
    hours if there is a large backlog of work to replicate.
    """
    return execute_slonik("""
        sync (id = 1);
        wait for event (
            origin = ALL, confirmed = ALL,
            wait on = @master_id, timeout = %d);
        """ % timeout)


def execute_slonik(script, sync=None, exit_on_fail=True):
    """Use the slonik command line tool to run a slonik script.

    :param script: The script as a string. Preamble should not be included.

    :param sync: Number of seconds to wait for sync before failing.
    """
    slonik_process = subprocess.Popen(
            ['slonik'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    if sync is not None:
        script = preamble() + script + """
            sync (id = 1);
            wait for event (
                origin = ALL, confirmed = ALL,
                wait on = @master_id, timeout = %d);
            """ % sync
    else:
        script = preamble() + script

    #log.debug("executing script:\n%s" % script)

    (out, err) = slonik_process.communicate(script)
    out = [line for line in out.strip().split('\n') if line]

    if slonik_process.returncode != 0:
        log.error("slonik script failed")
        for line in out:
            log.error(line)
        if exit_on_fail:
            sys.exit(1)
    elif out:
        for line in out:
            log.debug(line)

    return slonik_process.returncode == 0


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
