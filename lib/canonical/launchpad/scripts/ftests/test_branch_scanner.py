# Copyright 2006 Canonical Ltd.  All rights reserved.
# Author: David Allouche <david@allouche.net>

"""Feature tests for the Branch Scanner script."""

__metaclass__ = type


from os import mkdir
from os.path import dirname, join, isdir, exists
from shutil import rmtree, copytree
from subprocess import call, Popen, PIPE
from unittest import TestLoader

import transaction
from zope.component import getUtility
from canonical.config import config
from canonical.launchpad.interfaces import IBranchSet
from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase


class BranchScannerTest(LaunchpadFunctionalTestCase):

    def setUp(self):
        LaunchpadFunctionalTestCase.setUp(self)
        self.warehouse = None

    def setupWarehouse(self):
        warehouse_url = config.branchscanner.root_url
        assert warehouse_url.startswith('file://')
        warehouse = warehouse_url[len('file://'):]
        if isdir(warehouse):
            rmtree(warehouse)
        mkdir(warehouse)
        self.warehouse = warehouse

    def expandTestBranch(self, name):
        tarball = join(dirname(__file__), name + '.tgz')
        returncode = call(['tar', 'xzf', tarball], cwd=self.warehouse)
        assert returncode == 0
        assert isdir(join(self.warehouse, name))

    def installTestBranch(self, name, db_branch):
        origin = join(self.warehouse, name)
        destination = join(self.warehouse, '%08x' % db_branch.id)
        assert not exists(destination)
        returncode = call(['cp', '-a', origin, destination])
        assert returncode == 0

    def test_branch_scanner_script(self):
        """branch-scanner.py does something"""
        login(ANONYMOUS)
        self.setupWarehouse()
        self.expandTestBranch('onerev')        
        # setup a test branch for every branch record in the sampledata
        for branch in getUtility(IBranchSet):
            self.installTestBranch('onerev', branch)
        # run branch-scanner.py and check the process outputs
        script = join(config.root, 'cronscripts', 'branch-scanner.py')
        process = Popen([script, '-q'],
                        stdout=PIPE, stderr=PIPE, stdin=open('/dev/null'))
        output, error = process.communicate()
        status = process.returncode
        self.assertEqual((status, output ,error), (0, '', ''),
                         'baz2bzr existed with status=%d\n'
                         '>>>stdout<<<\n%s\n>>>stderr<<<\n%s'
                         % (status, output, error))
        # check that all branches were set to the test data
        transaction.abort()
        for db_branch in getUtility(IBranchSet):
            history = branch.revision_history
            self.assertEqual(history.count(), 1)
            revision = history[0].revision
            self.assertEqual(revision.log_body, 'Log message')


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
