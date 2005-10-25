# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Fill the database with information from Bazaar branch."""

import sys
import os
from datetime import datetime

from buildbot.process.base import ConfigurableBuildFactory, ConfigurableBuild
from buildbot.process.step import ShellCommand

from canonical.launchpad.database import Branch
from canonical.database.constants import UTC_NOW

from importd.util import (
    getTxnManager, tryToAbortTransaction,
    NotifyingBuild)

__all__ = ['bzrScanBuilders']

__metaclass__ = type


def bzrScanBuilders(slavenames, runner_path=None, periodic=None):
    builders = []
    getTxnManager().begin()
    try:
        branches = list(Branch.select())
        branches.sort(key=lambda x: x.id)
        for branch in branches:
            name = 'branch-%03d' % (branch.id,)
            slavename = slavenames[hash(name) % len(slavenames)]
            builddir = 'bzrscan-jobs'
            if runner_path is None:
                runner_path = os.path.join(
                    os.path.dirname(__file__), 'bzrsync.py')
            else:
                runner_path = str(runner_path)
            if periodic is None:
                periodic = 24 * 60 * 60 # one day
            branch_name = '%s %s %s' % (
                branch.owner.name, branch.product_name, branch.name)
            scanjob = {'id': branch.id, 'branch_name': branch_name,
                       'interval': periodic}
            factory = BzrScanBuildFactory(scanjob, runner_path)
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

    @property
    def buildClass(self):
        return BzrScanBuild

    def __init__(self, scanjob, runner_path):
        self.steps = []
        self.scanjob = scanjob
        self.runner_path = runner_path
        self.addSteps()

    def addSteps(self):
        self.steps.append((BzrScanShellCommand, {
            'timeout': 1200,
            'workdir': None,
            'branch_name': self.scanjob['branch_name'],
            'command': [sys.executable, self.runner_path,
                        str(self.scanjob['id'])]}))

    def newBuild(self):
        build = ConfigurableBuildFactory.newBuild(self)
        build.scanjob = self.scanjob
        return build


class BzrScanShellCommand(ShellCommand):

    def __init__(self, branch_name, **kwargs):
        ShellCommand.__init__(self, **kwargs)
        self.branch_name = branch_name

    def words(self):
        """Short display of BzrScan steps in buildbot."""
        return [self.branch_name]


class BzrScanBuild(NotifyingBuild):

    def getObserver(self):
        return BzrScanBuildObserver(self)


class BzrScanBuildObserver:

    def __init__(self, build):
        self.build = build
        scanjob = build.scanjob
        self.branch_id = scanjob['id']

    def startBuild(self):
        getTxnManager().begin()
        # do nothing
        getTxnManager().commit()

    def buildFinished(self, successful):
        getTxnManager().begin()
        self.setLastMirrorAttempt()
        getTxnManager().commit()

    def setLastMirrorAttempt(self):
        self.getBranch().last_mirror_attempt = UTC_NOW

    def getBranch(self):
        return Branch.get(self.branch_id)
