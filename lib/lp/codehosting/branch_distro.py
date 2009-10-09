# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX write me."""

import os

from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.errors import NotBranchError, NotStacked

import transaction

from zope.component import getUtility

from canonical.launchpad.interfaces import ILaunchpadCelebrities
from canonical.config import config

from lp.code.interfaces.branchcollection import IAllBranches
from lp.code.interfaces.branch import BranchExists
from lp.code.interfaces.branchnamespace import IBranchNamespaceSet
from lp.code.enums import BranchType
from lp.codehosting.vfs import branch_id_to_path
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.sourcepackage import ISourcePackageFactory

__metaclass__ = type
__all__ = []


def switch_branches(prefix, scheme, old_db_branch, new_db_branch):
    """Move bzr data from an old to a new branch, leaving old stacked on new.

    This function is intended to be used just after Ubuntu is released to
    create (at the bzr level) a new trunk branch for a source package for the
    next release of the distribution.  We move the bzr data to the location
    for the new branch and replace the trunk branch for the just released
    version with a stacked branch pointing at the new branch.

    :param prefix: The non-branch id dependent part of the physical path to
        the branches on disk.
    :param scheme: The branches should be open-able at
        ``scheme + unique_name``.
    :param old_db_branch: The branch that currently has the trunk bzr data.
    :param old_db_branch: The new trunk branch.  This should not have any
        presence on disk yet.
    """
    # Move .bzr directory from old to new locations, crashing through the
    # abstraction we usually hide our branch locations behind.
    old_underlying_path = os.path.join(
        prefix, branch_id_to_path(old_db_branch.id))
    new_underlying_path = os.path.join(
        prefix, branch_id_to_path(new_db_branch.id))
    os.makedirs(new_underlying_path)
    os.rename(
        os.path.join(old_underlying_path, '.bzr'),
        os.path.join(new_underlying_path, '.bzr'))

    # Create branch at old location -- we use the "clone('null:')" trick to
    # preserve the format.  We have to open at the logical, unique_name-based,
    # location so that it works to set the stacked on url to '/' + a
    # unique_name.
    new_location_bzrdir = BzrDir.open(scheme + new_db_branch.unique_name)
    old_location_bzrdir = new_location_bzrdir.clone(
        scheme + old_db_branch.unique_name, revision_id='null:')

    # Set the stacked on url for old location.
    old_location_branch = old_location_bzrdir.open_branch()
    old_location_branch.set_stacked_on_url('/' + new_db_branch.unique_name)

    # Pull from new location to old -- this won't actually transfer any
    # revisions, just update the last revision pointer.
    old_location_branch.pull(new_location_bzrdir.open_branch())


class DistroBrancher:
    """XXX."""

    def __init__(self, logger, old_distroseries, new_distroseries):
        """XXX."""
        self.logger = logger
        if old_distroseries.distribution != new_distroseries.distribution:
            raise AssertionError(
                "%s and %s are from different distributions!" %
                (old_distroseries, new_distroseries))
        self.old_distroseries = old_distroseries
        self.new_distroseries = new_distroseries

    def _existingOfficialBranches(self):
        """XXX."""
        branches = getUtility(IAllBranches)
        distroseries_branches = branches.inDistroSeries(self.old_distroseries)
        return distroseries_branches.officialBranches().getBranches()

    def makeNewBranches(self):
        """XXX."""
        for db_branch in self._existingOfficialBranches():
            self.logger.debug("Processing %r" % db_branch)
            try:
                self.makeOneNewBranch(db_branch)
            except BranchExists:
                # Check here?
                pass

    def checkConsistentOfficialPackageBranch(self, db_branch):
        """XXX."""
        if db_branch.product:
            self.logger.warning(
                "Encountered unexpected product branch %r",
                db_branch.unique_name)
            return False
        if not db_branch.distroseries:
            self.logger.warning(
                "Encountered unexpected personal branch %r",
                db_branch.unique_name)
            return False
        package_branch = db_branch.sourcepackage.getBranch(
            PackagePublishingPocket.RELEASE)
        if package_branch != db_branch:
            self.logger.warning(
                "%r is not the official branch for its sourcepackage (%r"
                " is instead)", db_branch.unique_name,
                package_branch.unique_name)
            return False
        return True

    def checkNewBranches(self):
        """XXX."""
        ok = True
        for db_branch in self._existingOfficialBranches():
            try:
                if not self.checkOneBranch(db_branch):
                    ok = False
            except:
                ok = False
                self.logger.error("Unexpected error checking %s!", db_branch)
        return ok

    def checkOneBranch(self, old_db_branch):
        """XXX."""
        new_sourcepackage = getUtility(ISourcePackageFactory).new(
            sourcepackagename=old_db_branch.sourcepackagename,
            distroseries=self.new_distroseries)
        new_db_branch = new_sourcepackage.getBranch(
            PackagePublishingPocket.RELEASE)
        if new_db_branch is None:
            self.logger.warning(
                "No official branch found for %s" % new_sourcepackage)
            return False
        ok = self.checkConsistentOfficialPackageBranch(new_db_branch)
        # for both mirrored and hosted areas:
        for scheme in 'lp-mirrored', 'lp-hosted':
            # the branch in the new distroseries is unstacked
            try:
                new_bzr_branch = Branch.open(
                    scheme + new_db_branch.unique_name)
            except NotBranchError:
                self.logger.warning("No bzr branch for %s", new_bzr_branch)
                ok = False
            else:
                try:
                    new_stacked_on_url = new_bzr_branch.get_stacked_on_url()
                    self.logger.warning(
                        "%s is stacked on %s", new_bzr_branch,
                        new_stacked_on_url)
                except NotStacked:
                    pass
            # The branch in the old distroseries is stacked on that in the
            # new.
            try:
                old_bzr_branch = Branch.open(
                    scheme + old_db_branch.unique_name)
            except NotBranchError:
                self.logger.warning("No bzr branch for %s", new_bzr_branch)
                ok = False
            else:
                try:
                    old_stacked_on_url = old_bzr_branch.get_stacked_on_url()
                    # XXX next line could NameError!
                    if old_stacked_on_url != '/' + new_bzr_branch.unique_name:
                        self.logger.warning(
                            "%s is stacked on %s, should be %s",
                            old_bzr_branch, old_stacked_on_url,
                            '/' + new_bzr_branch.unique_name)
                        ok = False
                except NotStacked:
                    self.logger.warning("%s is not stacked", old_bzr_branch)
                    ok = False
                    # The branch in the old distroseries has no revisions in
                    # its repository.  This might fail if new revisions get
                    # pushed to the branch in the old distroseries, which
                    # shouldn't happen but isn't totally impossible.
                    if len(old_bzr_branch.repository.all_revision_ids()) > 0:
                        self.logger.warning("XXX")
                        ok = False
                    # The branch in the old distroseries has at least some
                    # history.  (We can't check that the tips are the same
                    # because the branch in the new distroseries might have
                    # new revisons).
                    if old_bzr_branch.last_revision() == 'null:':
                        self.logger.warning("XXX")
                        ok = False
        return ok

    def makeOneNewBranch(self, old_db_branch):
        """XXX."""
        new_namespace = getUtility(IBranchNamespaceSet).get(
            person=old_db_branch.owner, product=None,
            distroseries=self.new_distroseries,
            sourcepackagename=old_db_branch.sourcepackagename)
        new_db_branch = new_namespace.createBranch(
            BranchType.HOSTED, old_db_branch.name, old_db_branch.registrant)
        # XXX What to pass as registrant?
        new_db_branch.sourcepackage.setBranch(
            PackagePublishingPocket.RELEASE, new_db_branch,
            getUtility(ILaunchpadCelebrities).ubuntu_branches.teamowner)
        # Commit now because switch_branches *moves* the data to locations
        # dependent on the new_branch's id, so if the transaction doesn't get
        # committed we won't know where it's gone.
        transaction.commit()
        switch_branches(
            config.codehosting.hosted_branches_root,
            'lp-hosted:///', old_db_branch, new_db_branch)
        switch_branches(
            config.codehosting.mirrored_branches_root,
            'lp-mirrored:///', old_db_branch, new_db_branch)
