#!/usr/bin/env python2.3
# Copyright 2004 Canonical Ltd.  All rights reserved.

"""Tests that get run automatically on a merge."""

import sys
import os, os.path
import tabnanny
import checkarchtag
from StringIO import StringIO

def main():
    """Call test.py with whatever arguments this script was run with.

    If the tests ran ok (last line of stderr is 'OK<return>') then suppress
    output and exit(0).

    Otherwise, print output and exit(1).
    """
    here = os.path.dirname(os.path.realpath(__file__))

    if not checkarchtag.is_tree_good():
        return 1

    here = os.path.dirname(os.path.realpath(__file__))
    schema_dir = os.path.join(here, 'database', 'schema')
    if os.system('cd %s; make test > /dev/null 2>&1' % schema_dir) != 0:
        print 'Failed to create database'
        return 1

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

    print 'Running tests.'
    stdin, out, err = os.popen3('cd %s; python test.py %s < /dev/null' %
        (here, ' '.join(sys.argv[1:])))
    errlines = err.readlines()
    dataout = out.read()
    test_ok = errlines[-1] == 'OK\n'

    if test_ok:
        print errlines[1]
        return 0
    else:
        print '---- test stdout ----'
        print dataout
        print '---- end test stdout ----'

        print '---- test stderr ----'
        print ''.join(errlines)
        print '---- end test stderr ----'
        return 1

if __name__ == '__main__':
    sys.exit(main())
