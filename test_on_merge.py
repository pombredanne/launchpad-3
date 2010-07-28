#!/usr/bin/python -S
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


# The TIMEOUT setting (expressed in seconds) affects how long a test will run
# before it is deemed to be hung, and then appropriately terminated.
# It's principal use is preventing a PQM job from hanging indefinitely and
# backing up the queue.
# e.g. Usage: TIMEOUT = 60 * 10
# This will set the timeout to 10 minutes.
TIMEOUT = 60 * 10

HERE = os.path.dirname(os.path.realpath(__file__))


def main():
    """Call bin/test with whatever arguments this script was run with.

    Prior to running the tests this script checks the project files with
    Python2.5's tabnanny and sets up the test database.

    Returns 1 on error, otherwise it returns the testrunner's exit code.
    """
    if run_tabnanny() != 0:
        return 1

    if setup_test_database() != 0:
        return 1

    return run_test_process()


def run_tabnanny():
    """Run the tabnanny, return its exit code.

    If tabnanny raises an exception, run "python /usr/lib/python2.5/tabnanny.py
    -vv lib/canonical for more detailed output.
    """
    # XXX mars 2010-05-26
    # Tabnanny reports some of its errors on sys.stderr, so this code is
    # already wrong.  subprocess.Popen.communicate() would work better.
    print "Checking the source tree with tabnanny..."
    org_stdout = sys.stdout
    sys.stdout = StringIO()
    tabnanny.check(os.path.join(HERE, 'lib', 'canonical'))
    tabnanny.check(os.path.join(HERE, 'lib', 'lp'))
    tabnanny_results = sys.stdout.getvalue()
    sys.stdout = org_stdout
    if len(tabnanny_results) > 0:
        print '---- tabnanny bitching ----'
        print tabnanny_results
        print '---- end tabnanny bitching ----'
        return 1
    else:
        print "Done"
        return 0


def setup_test_database():
    """Set up a test instance of our postgresql database.

    Returns 0 for success, 1 for errors.
    """
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
    schema_dir = os.path.join(HERE, 'database', 'schema')
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

    return 0


def run_test_process():
    """Start the testrunner process and return its exit code."""
    # Fork a child process so that we get a new process ID that we can
    # guarantee is not currently in use as a process group leader. This
    # addresses the case where this script has been started directly in the
    # shell using "python foo.py" or "./foo.py".
    pid = os.fork()
    if pid != 0:
        # We are the parent process, so we'll wait for our child process to
        # do the heavy lifting for us.
        pid, status = os.wait()

        if os.WIFEXITED(status):
            return os.WEXITSTATUS(status)
        else:
            # We should not reach this code unless something segfaulted in
            # our child process, or it recieved a signal from some outside
            # force.
            raise RuntimeError(
                "Oops!  The test watchdog was killed by signal %s" % (
                    os.WTERMSIG(status)))

    print 'Running tests.'
    os.chdir(HERE)

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
        "--error-file=/var/tmp/xvfb-errors.log",
        "--server-args='-screen 0 1024x768x24'",
        os.path.join(HERE, 'bin', 'test')] + sys.argv[1:]
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

    # This code is very similar to what takes place in Popen._communicate(),
    # but this code times out if there is no activity on STDOUT for too long.
    open_readers = set([xvfb_proc.stdout])
    while open_readers:
        rlist, wlist, xlist = select(open_readers, [], [], TIMEOUT)

        if len(rlist) == 0:
            # The select() statement timed out!

            if xvfb_proc.poll() is not None:
                # The process we were watching died.
                break

            cleanup_hung_testrunner(xvfb_proc)
            break

        if xvfb_proc.stdout in rlist:
            # Read a chunk of output from STDOUT.
            chunk = os.read(xvfb_proc.stdout.fileno(), 1024)
            sys.stdout.write(chunk)
            if chunk == "":
                # Gracefully exit the loop if STDOUT is empty.
                open_readers.remove(xvfb_proc.stdout)

    rv = xvfb_proc.wait()

    if rv == 0:
        print
        print 'Successfully ran all tests.'
    else:
        print
        print 'Tests failed (exit code %d)' % rv

    return rv


def cleanup_hung_testrunner(process):
    """Kill and clean up the testrunner process and its children."""
    print
    print
    print ("WARNING: A test appears to be hung. There has been no "
        "output for %d seconds." % TIMEOUT)
    print "Forcibly shutting down the test suite"

    # This guarantees the process' group will die.  In rare cases
    # a child process may survive this if they are in a different
    # process group and they ignore the signals we send their parent.
    nice_killpg(process)

    # Drain the subprocess's stdout and stderr.
    print "The dying processes left behind the following output:"
    print "--------------- BEGIN OUTPUT ---------------"
    sys.stdout.write(process.stdout.read())
    print
    print "---------------- END OUTPUT ----------------"


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
