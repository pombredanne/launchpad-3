# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Script executed by test_remote.py to verify daemonization behaviour.

See TestDaemonizationInteraction.
"""

import os
import sys
import traceback

from devscripts.ec2test.remote import EC2Runner, WebTestLogger
from devscripts.ec2test.tests.test_remote import TestRequest

PID_FILENAME = os.path.abspath(sys.argv[1])
DIRECTORY = os.path.abspath(sys.argv[2])
LOG_FILENAME = os.path.abspath(sys.argv[3])


def make_request():
    """Just make a request."""
    test = TestRequest('test_wants_email')
    test.setUp()
    try:
        return test.make_request()
    finally:
        test.tearDown()


def prepare_files(logger):
    try:
        logger.prepare()
    except:
        # If anything in the above fails, we want to be able to find out about
        # it.  We can't use stdout or stderr because this is a daemon.
        error_log = open(LOG_FILENAME, 'w')
        traceback.print_exc(file=error_log)
        error_log.close()


request = make_request()
os.mkdir(DIRECTORY)
logger = WebTestLogger.make_in_directory(DIRECTORY, request, True)
runner = EC2Runner(
    daemonize=True,
    pid_filename=PID_FILENAME,
    shutdown_when_done=False)
runner.run("test daemonization interaction", prepare_files, logger)
