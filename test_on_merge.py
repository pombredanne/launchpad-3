#!/usr/bin/env python2.3
# Copyright 2004 Canonical Ltd.  All rights reserved.

"""Tests that get run automatically on a merge."""

import sys
import os, os.path
import popen2
import tabnanny
import checkarchtag
from StringIO import StringIO
from threading import Thread

class NonBlockingReader(Thread):

    result = None

    def __init__(self,file):
        Thread.__init__(self)
        self.file = file

    def run(self):
        self.result = self.file.read()

    def read(self):
        if self.result is None:
            raise RuntimeError("read() called before run()")
        return self.result

    def readlines(self):
        if self.result is None:
            raise RuntimeError("readlines() called before run()")
        return self.result.splitlines()


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
    proc = popen2.Popen3('cd %s; python test.py %s < /dev/null' %
        (here, ' '.join(sys.argv[1:])), True)
    stdin, out, err = proc.tochild, proc.fromchild, proc.childerr

    # Use non-blocking reader threads to cope with differing expectations
    # from the proess of when to consume data from out and error.
    errthread = NonBlockingReader(err)
    outthread = NonBlockingReader(out)
    errthread.start()
    outthread.start()
    errthread.join()
    outthread.join()
    exitcode = proc.wait()
    test_ok = (os.WIFEXITED(exitcode) and os.WEXITSTATUS(exitcode) == 0)

    errlines = errthread.readlines()
    dataout = outthread.read()

    if test_ok:
        print errlines[1]
        return 0
    else:
        print '---- test stdout ----'
        print dataout
        print '---- end test stdout ----'

        print '---- test stderr ----'
        print '\n'.join(errlines)
        print '---- end test stderr ----'
        return 1

if __name__ == '__main__':
    sys.exit(main())
