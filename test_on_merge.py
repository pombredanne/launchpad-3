#!/usr/bin/python2.4
# Copyright 2004 Canonical Ltd.  All rights reserved.

"""Tests that get run automatically on a merge."""

import sys, time
import os, errno
import tabnanny
from StringIO import StringIO
import psycopg2
from subprocess import Popen, PIPE, STDOUT
from signal import SIGKILL, SIGTERM
from select import select

# The TIMEOUT setting (expressed in seconds) affects how long a test will run
# before it is deemed to be hung, and then appropriately terminated.
# It's principal use is preventing a PQM job from hanging indefinitely and
# backing up the queue.
# e.g. Usage: TIMEOUT = 60 * 15
# This will set the timeout to 15 minutes.
TIMEOUT = 60 * 15

def main():
    """Call test.py with whatever arguments this script was run with.

    If the tests ran ok (last line of stderr is 'OK<return>') then suppress
    output and exit(0).

    Otherwise, print output and exit(1).
    """
    here = os.path.dirname(os.path.realpath(__file__))

    # Tabnanny
    # NB. If tabnanny raises an exception, run
    # python /usr/lib/python2.4/tabnanny.py -vv lib/canonical
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
    if os.system('cd %s; make test PYTHON=%s > /dev/null' % (
        schema_dir, sys.executable)) != 0:
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
    cmd = [sys.executable, 'test.py'] + sys.argv[1:]
    print ' '.join(cmd)

    # Run the test suite and return the error code
    #return call(cmd)

    proc = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    proc.stdin.close()

    # Do proc.communicate(), but timeout if there's no activity on stdout or
    # stderr for too long.
    open_readers = set([proc.stdout])
    while open_readers:
        rlist, wlist, xlist = select(open_readers, [], [], TIMEOUT)

        if len(rlist) == 0:
            if proc.poll() is not None:
                break
            print ("\nA test appears to be hung. There has been no output for"
                " %d seconds. Sending SIGTERM." % TIMEOUT)
            killem(proc.pid, SIGTERM)
            time.sleep(3)
            if proc.poll() is not None:
                print ("\nSIGTERM did not work. Sending SIGKILL.")
                killem(proc.pid, SIGKILL)
            # Drain the subprocess's stdout and stderr.
            sys.stdout.write(proc.stdout.read())
            break

        if proc.stdout in rlist:
            chunk = os.read(proc.stdout.fileno(), 1024)
            sys.stdout.write(chunk)
            if chunk == "":
                open_readers.remove(proc.stdout)

    rv = proc.wait()
    if rv == 0:
        print '\nSuccessfully ran all tests.'
    else:
        print '\nTests failed (exit code %d)' % rv

    return rv


def killem(pid, signal):
    """Kill the process group leader identified by pid and other group members

    Note that test.py sets its process to a process group leader.
    """
    try:
        os.killpg(os.getpgid(pid), signal)
    except OSError, x:
        if x.errno == errno.ESRCH:
            pass
        else:
            raise

if __name__ == '__main__':
    sys.exit(main())
