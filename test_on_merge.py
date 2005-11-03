#!/usr/bin/env python2.3
# Copyright 2004 Canonical Ltd.  All rights reserved.

"""Tests that get run automatically on a merge."""

import sys, re, time
import os, os.path, errno
import tabnanny
from StringIO import StringIO
import psycopg
from subprocess import Popen, PIPE
from signal import SIGKILL, SIGTERM
from select import select

# Die and kill the kids if no output for 10 minutes. Tune this if if your
# slow arsed machine needs it. The main use for this is to keep the pqm
# queue flowing without having to give it a lifeless enema.
TIMEOUT = 10 * 60 

def main():
    """Call test.py with whatever arguments this script was run with.

    If the tests ran ok (last line of stderr is 'OK<return>') then suppress
    output and exit(0).

    Otherwise, print output and exit(1).
    """
    here = os.path.dirname(os.path.realpath(__file__))

    # Tabnanny
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

    # Ensure ++resource++ URL's are all absolute - this ensures they
    # are cache friendly
    results = os.popen(
        "find lib/canonical -type f | xargs grep '[^/]++resource++'"
        ).readlines()
    if results:
        print '---- non-absolute ++resource++ URLs found ----'
        print ''.join(results)
        print '---- end non-absolute ++resource++ URLs found ----'
        return 1

    # Sanity check PostgreSQL version. No point in trying to create a test
    # database when PostgreSQL is too old.
    con = psycopg.connect('dbname=template1')
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
        if numeric_server_version < (7, 4):
            print 'Your PostgreSQL version is too old.  You need 7.4.x'
            print 'You have %s' % server_version
            return 1

    # Drop the template database if it exists - the Makefile does this
    # too, but we can explicity check for errors here
    con = psycopg.connect('dbname=template1')
    con.set_isolation_level(0)
    cur = con.cursor()
    try:
        cur.execute('drop database launchpad_ftest_template')
    except psycopg.ProgrammingError, x:
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
    con = psycopg.connect('dbname=launchpad_ftest_template')
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
    if enc != 'UNICODE':
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
    # This would be simpler if we set stderr=STDOUT to combine the streams
    proc = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    proc.stdin.close()

    out =  [] # stdout from tests
    err = [] # stderr from tests
    open_readers = set([proc.stderr, proc.stdout])
    while open_readers:
        rlist, wlist, xlist = select(open_readers, [], [], TIMEOUT)

        if len(rlist) == 0:
            if proc.poll() is None:
                break
            print 'Tests hung - no output for %d seconds. Killing.' % TIMEOUT
            killem(proc.pid, SIGTERM)
            time.sleep(3)
            if proc.poll() is None:
                print 'Not dead yet! - slaughtering mercilessly'
                killem(proc.pid, SIGKILL)
            break

        if proc.stdout in rlist:
            out.append(os.read(proc.stdout.fileno(), 1024))
            if out[-1] == "":
                open_readers.remove(proc.stdout)
        if proc.stderr in rlist:
            err.append(os.read(proc.stderr.fileno(), 1024))
            if err[-1] == "":
                open_readers.remove(proc.stderr)

    test_ok = (proc.wait() == 0)

    out = ''.join(out)
    err = ''.join(err)

    if test_ok:
        for line in err.split('\n'):
            if re.match('^Ran\s\d+\stest(s)?\sin\s[\d\.]+s$', line):
                print line
        return 0
    else:
        print '---- test stdout ----'
        print out
        print '---- end test stdout ----'

        print '---- test stderr ----'
        print err
        print '---- end test stderr ----'
        return 1

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
