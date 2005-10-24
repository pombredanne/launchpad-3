# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Fill the database with information from Bazaar branch."""

import sys
import os

from buildbot.process.base import ConfigurableBuildFactory, ConfigurableBuild
from buildbot.process.step import ShellCommand

from canonical.launchpad.database import Branch

from importd.util import getTxnManager, tryToAbortTransaction

__all__ = ['bzrScanBuilders']

__metaclass__ = type


def bzrScanBuilders(slavenames, runner_path=None, periodic=None):
    builders = []
    getTxnManager().begin()
    try:
        for branch in Branch.select():
            name = 'branch-%d' % (branch.id,)
            slavename = slavenames[hash(name) % len(slavenames)]
            builddir = 'bzrscan-jobs'
            if periodic is None:
                periodic = 24 * 60 * 60 # one day
            branch_name = '%s %s %s' % (
                branch.owner.name, branch.product_name, branch.name)
            factory = BzrScanBuildFactory(branch.id, branch_name, runner_path)
            builderDict = {'name': name, 'slavename': slavename,
                           'builddir': builddir, 'factory': factory,
                           'periodicBuildTime': periodic}
            builders.append(builderDict)
        getTxnManager().abort()
    except:
        tryToAbortTransaction()
        raise        
    return builders


class BzrScanBuildFactory(ConfigurableBuildFactory):

    def __init__(self, branch_id, branch_name, runner_path):
        self.steps = []
        self.branch_id = branch_id
        self.branch_name = branch_name
        if runner_path is None:
            self.runner_path = os.path.join(os.path.dirname(__file__),
                                            'bzrsync.py')
        else:
            self.runner_path = str(runner_path)
        self.addBzrScanStep()

    def addBzrScanStep(self):
        self.steps.append((BzrScanShellCommand, {
            'timeout': 1200,
            'workdir': None,
            'branch_name': self.branch_name,
            'command': [sys.executable, self.runner_path,
                        str(self.branch_id)]}))
        


class BzrScanShellCommand(ShellCommand):

    def __init__(self, branch_name, **kwargs):
        ShellCommand.__init__(self, **kwargs)
        self.branch_name = branch_name

    def words(self):
        """Short display of BzrScan steps in buildbot."""
        return [self.branch_name]
