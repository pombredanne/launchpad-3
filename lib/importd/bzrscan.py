# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Fill the database with information from a Bazaar branch."""

__metaclass__ = type

__all__ = ['bzrScanBuilders']

import sys
import os
from datetime import datetime

from buildbot.process.base import ConfigurableBuildFactory, ConfigurableBuild
from buildbot.process.step import ShellCommand

from canonical.launchpad.database import Branch
from canonical.database.constants import UTC_NOW

from importd.util import (
    getTxnManager, tryToAbortTransaction, NotifyingBuild)


def bzrScanBuilders(slavenames, runner_path=None, periodic=None):
    builders = []
    getTxnManager().begin()
    try:
        branches = list(Branch.select())
        branches.sort(key=lambda branch: branch.id)
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
                periodic = 24 * 60 * 60 # one day in seconds
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
        # Safely abort the transaction and re-raise the exception. 
        tryToAbortTransaction()
        raise
    return builders


class BzrScanBuildFactory(ConfigurableBuildFactory):
    """Factory for Buildbot Build objects that run bzrsync."""

    @property
    def buildClass(self):
        """Type used by inherited newBuild to instanciate a Build object."""
        return BzrScanBuild

    def __init__(self, scanjob, runner_path):
        self.steps = []
        self.scanjob = scanjob
        self.runner_path = runner_path
        self.addSteps()

    def addSteps(self):
        """Add a single build step that runs bzrsync in a process.

        The bzrsync process will be killed if it produces no output during the
        number of seconds specified as 'timeout'.
        """
        command = [sys.executable, self.runner_path, str(self.scanjob['id'])]
        self.steps.append((BzrScanShellCommand, {
            'timeout': 1200,
            'workdir': None,
            'branch_name': self.scanjob['branch_name'],
            'command': command}))

    def newBuild(self):
        """Make a new Build instance.

        Pass in job information in scanjob to allow the Build to update the
        database with status information."""
        build = ConfigurableBuildFactory.newBuild(self)
        build.scanjob = self.scanjob
        return build


class BzrScanShellCommand(ShellCommand):
    """Shell command with custom short display."""

    def __init__(self, branch_name, **kwargs):
        ShellCommand.__init__(self, **kwargs)
        self.branch_name = branch_name

    def words(self):
        """Short display of BzrScan steps in buildbot."""
        # Buildbot requires this method to return a sequence of words.
        return [self.branch_name]


class BzrScanBuild(NotifyingBuild):
    """Build that notify a BzrScanBuildObserver of build starts and stops."""

    def getObserver(self):
        """Object to send notifications to.

        startBuild is called before the build starts.
        
        buildFinished is called after the build complete, with a boolean
        argument indicating whether the build was successful.
        """
        return BzrScanBuildObserver(self)


class BzrScanBuildObserver:
    """Update the database when a Bazaar sync build starts or finish."""

    def __init__(self, build):
        self.build = build
        scanjob = build.scanjob
        self.branch_id = scanjob['id']

    def startBuild(self):
        """Called before a sync starts."""
        getTxnManager().begin()
        # Do nothing. When this method exits it's required that the current
        # process has started a transaction at least once.
        getTxnManager().commit()

    def buildFinished(self, successful):
        """Called after a sync finishes.

        The 'successful' parameter is false if the sync process was not
        successful.
        """
        getTxnManager().begin()
        self.setLastMirrorAttempt()
        getTxnManager().commit()

    def setLastMirrorAttempt(self):
        """Set the last_mirror_attempt timestamp of the synced branch."""
        self.getBranch().last_mirror_attempt = UTC_NOW

    def getBranch(self):
        """The database Branch object associated to this sync build."""
        return Branch.get(self.branch_id)
