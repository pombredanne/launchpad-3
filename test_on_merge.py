#!/usr/bin/python2.5 -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests that get run automatically on a merge."""
import _pythonpath

import sys, time
import os, errno
import tabnanny
from StringIO import StringIO
import psycopg2
from subprocess import Popen, PIPE, STDOUT
from signal import SIGKILL, SIGTERM, SIGINT, SIGHUP
from select import select


__metaclass__ = type


# The TIMEOUT setting (expressed in seconds) affects how long a test will run
# before it is deemed to be hung, and then appropriately terminated.
# It's principal use is preventing a PQM job from hanging indefinitely and
# backing up the queue.
# e.g. Usage: TIMEOUT = 60 * 15
# This will set the timeout to 15 minutes.
#TIMEOUT = 60 * 150
TIMEOUT = 60


def main():
    """Call bin/test with whatever arguments this script was run with.

    If the tests ran ok (last line of stderr is 'OK<return>') then suppress
    output and exit(0).

    Otherwise, print output and exit(1).
    """
    here = os.path.dirname(os.path.realpath(__file__))

    # Tabnanny
    # NB. If tabnanny raises an exception, run
    # python /usr/lib/python2.5/tabnanny.py -vv lib/canonical
    # for more detailed output.
    org_stdout = sys.stdout
    sys.stdout = StringIO()
    tabnanny.check(os.path.join(here, 'lib', 'canonical'))
    tabnanny_results = sys.stdout.getvalue()
    sys.stdout = org_stdout
    if len(tabnanny_results) > 0:
        print '---- tabnanny bitching ----'
        print tabnanny_results
        print '---- end tabnanny bitching ----'
        return 1

    # Sanity check PostgreSQL version. No point in trying to create a test
    # database when PostgreSQL is too old.
    con = psycopg2.connect('dbname=template1')
    cur = con.cursor()
    cur.execute('show server_version')
    server_version = cur.fetchone()[0]
    try:
        numeric_server_version = tuple(map(int, server_version.split('.')))
    except ValueError:
        # Skip this check if the version number is more complicated than
        # we expected.
        pass
    else:
        if numeric_server_version < (8, 0):
            print 'Your PostgreSQL version is too old.  You need 8.x.x'
            print 'You have %s' % server_version
            return 1

    # Drop the template database if it exists - the Makefile does this
    # too, but we can explicity check for errors here
    con = psycopg2.connect('dbname=template1')
    con.set_isolation_level(0)
    cur = con.cursor()
    try:
        cur.execute('drop database launchpad_ftest_template')
    except psycopg2.ProgrammingError, x:
        if 'does not exist' not in str(x):
            raise
    cur.execute("""
        select count(*) from pg_stat_activity
        where datname in ('launchpad_dev',
            'launchpad_ftest_template', 'launchpad_ftest')
        """)
    existing_connections = cur.fetchone()[0]
    if existing_connections > 0:
        print 'Cannot rebuild database. There are %d open connections.' % (
                existing_connections,
                )
        return 1
    cur.close()
    con.close()

    # Build the template database. Tests duplicate this.
    here = os.path.dirname(os.path.realpath(__file__))
    schema_dir = os.path.join(here, 'database', 'schema')
    if os.system('cd %s; make test > /dev/null' % (schema_dir)) != 0:
        print 'Failed to create database or load sampledata.'
        return 1

    # Sanity check the database. No point running tests if the
    # bedrock is crumbling.
    con = psycopg2.connect('dbname=launchpad_ftest_template')
    cur = con.cursor()
    cur.execute('show search_path')
    search_path = cur.fetchone()[0]
    if search_path != '$user,public,ts2':
        print 'Search path incorrect.'
        print 'Add the following line to /etc/postgresql/postgresql.conf:'
        print "    search_path = '$user,public,ts2'"
        print "and tell postgresql to reload its configuration file."
        return 1
    cur.execute("""
        select pg_encoding_to_char(encoding) as encoding from pg_database
        where datname='launchpad_ftest_template'
        """)
    enc = cur.fetchone()[0]
    if enc not in ('UNICODE', 'UTF8'):
        print 'Database encoding incorrectly set'
        return 1
    cur.execute(r"""
        SELECT setting FROM pg_settings
        WHERE context='internal' AND name='lc_ctype'
        """)
    loc = cur.fetchone()[0]
    #if not (loc.startswith('en_') or loc in ('C', 'en')):
    if loc != 'C':
        print 'Database locale incorrectly set. Need to rerun initdb.'
        return 1

    # Explicity close our connections - things will fail if we leave open
    # connections.
    cur.close()
    del cur
    con.close()
    del con

    print 'Running tests.'
    os.chdir(here)

    # Play shenanigans with our process group. We want to kill off our child
    # groups while at the same time not slaughtering ourselves!
    original_process_group = os.getpgid(0)

    # Make sure we are not already the process group leader.  Otherwise this
    # trick won't work.
    assert original_process_group != os.getpid()

    # Change our process group to match our PID, as per POSIX convention.
    os.setpgrp()

    # We run the test suite under a virtual frame buffer server so that the
    # JavaScript integration test suite can run.
    cmd = [
        'xvfb-run',
        '-s',
        "'-screen 0 1024x768x24'",
        os.path.join(here, 'bin', 'test')] + sys.argv[1:]

    command_line = ' '.join(cmd)
    print "Running command:", command_line

    # Run the test suite and return the error code
    xvfb_proc = Popen(
        command_line, stdin=PIPE, stdout=PIPE, stderr=STDOUT, shell=True)
    xvfb_proc.stdin.close()

    # Restore our original process group, thus removing ourselves from
    # os.killpg's target list.  Our child process and its children will retain
    # the process group number matching our PID.
    os.setpgid(0, original_process_group)

    # This code is very similar to what takes place in proc._communicate(),
    # but this code times out if there is no activity on STDOUT for too long.
    open_readers = set([xvfb_proc.stdout])
    while open_readers:
        rlist, wlist, xlist = select(open_readers, [], [], TIMEOUT)

        if len(rlist) == 0:
            # The select() statement timed out!

            if xvfb_proc.poll() is not None:
                # The process we were watching died.
                break

            print
            print ("WARNING: A test appears to be hung. There has been no "
                "output for %d seconds." % TIMEOUT)
            print "Forcibly shutting down the test suite:"

            # This guarantees the processes the group will die.  In rare cases
            # a child process may survive this if they are in a different
            # process group and they ignore the signals we send their parent.
            nice_killpg(xvfb_proc)

            # Drain the subprocess's stdout and stderr.
            print "The dying processes left behind the following output:"
            print "--------------- BEGIN OUTPUT ---------------"
            sys.stdout.write(xvfb_proc.stdout.read())
            print "---------------- END OUTPUT ----------------"

            break

        if xvfb_proc.stdout in rlist:
            # Read a chunk of output from STDOUT.
            chunk = os.read(xvfb_proc.stdout.fileno(), 1024)
            sys.stdout.write(chunk)
            if chunk == "":
                # Gracefully exit the loop if STDOUT is empty.
                open_readers.remove(xvfb_proc.stdout)

    try:
        rv = xvfb_proc.wait()
    except OSError, exc:
        raise
        if exc.errno == errno.ECHILD:
            # The process has already died and been collected.
            rv = xvfb_proc.returncode
        else:
            raise

    if rv == 0:
        print
        print 'Successfully ran all tests.'
    else:
        print
        print 'Tests failed (exit code %d)' % rv

    return rv


def nice_killpg(process):
    """Kill a Unix process group using increasingly harmful signals."""
    pgid = os.getpgid(process.pid)

    try:
        print "Process group %d will be killed" % pgid

        # Attempt a series of increasingly brutal methods of killing the
        # process.
        for signum in [SIGTERM, SIGINT, SIGHUP, SIGKILL]:
            print "Sending signal %s to process group %d" % (signum, pgid)
            os.killpg(pgid, signum)

            # Give the processes some time to shut down.
            time.sleep(3)

            # Poll our original child process so that the Popen object can
            # capture the process' exit code. If we do not do this now it
            # will be lost by the following call to os.waitpid(). Note that
            # this also reaps every process in the process group!
            process.poll()

            # This call will raise ESRCH if the group is empty, or ECHILD if
            # the group has already been reaped. The exception will exit the
            # loop for us.
            os.waitpid(-pgid, os.WNOHANG)   # Check for survivors.

            print "Some processes ignored our signal!"

    except OSError, exc:
        if exc.errno == errno.ESRCH:
            # We tried to call os.killpg() and found the group to be empty.
            pass
        elif exc.errno == errno.ECHILD:
            # We tried to poll the process group with os.waitpid() and found
            # it was empty.
            pass
        else:
            raise
    print "Process group %d is now empty." % pgid


if __name__ == '__main__':
    sys.exit(main())
