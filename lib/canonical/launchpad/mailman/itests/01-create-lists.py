#! /usr/bin/env python
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Launchpad-Mailman integration test #1

Check that Mailman actually creates approved mailing lists.
"""

import os
import sys
import time
import datetime
import xmlrpclib

from subprocess import Popen, PIPE, STDOUT


XMLRPC_URL = 'http://xmlrpc.launchpad.dev:8087/mailinglists'
MAILMAN_BIN = os.path.normpath(os.path.join(
    os.path.dirname(sys.argv[0]), '../../../../', 'mailman', 'bin'))


proxy = xmlrpclib.ServerProxy(XMLRPC_URL)

# Step 1: Create two teams and an approved mailing list for each.  Ensure that
# Mailman creates the mailing lists.
proxy.testStep(1)
# Ask only for advertised lists so the site list doesn't show up here.  Also,
# print only the list names, no descriptions (i.e. 'bare').  Do this for about
# 20 seconds or until the lists exist.
until = datetime.datetime.now() + datetime.timedelta(seconds=20)
team_names = None
while datetime.datetime.now() < until:
    proc = Popen(('./list_lists', '-a', '-b'),
                 stdout=PIPE, stderr=STDOUT,
                 cwd=MAILMAN_BIN)
    stdout, stderr = proc.communicate()
    team_names = sorted(stdout.splitlines())
    if team_names == ['team-one', 'team-two']:
        break
if team_names == ['team-one', 'team-two']:
    print 'STEP 1; team creation: PASSED'
else:
    print 'STEP 1; team creation: FAILED'

# XXX To clean up from this test, you must:
# bin/rmlist -a team-one
# bin/rmlist -a team-two
# make schema
