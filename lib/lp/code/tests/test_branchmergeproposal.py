# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for methods of BranchMergeProposal."""


from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing import DatabaseFunctionalLayer

from lp.code.interfaces.linkedbranch import ICanHasLinkedBranch
from lp.code.tests.test_branch import PermissionTest
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet
from lp.testing import run_with_login


class TestEditMergeProposal(PermissionTest):
    """Test who can edit branchmergeproposals."""

    layer = DatabaseFunctionalLayer

    def test_packge_upload_permissions_grant_merge_proposal_edit(self):
        # If you can upload to the package then you can edit merge
        # proposals against the official branch.

        permission_set = getUtility(IArchivePermissionSet)
        # Only admins or techboard members can add permissions normally. That
        # restriction isn't relevant to these tests.
        self.permission_set = removeSecurityProxy(permission_set)
        branch = self.factory.makePackageBranch()
        # Make sure the (distroseries, pocket) combination used allows us to
        # upload to it.
        stable_states = (
            SeriesStatus.SUPPORTED, SeriesStatus.CURRENT)
        if branch.distroseries.status in stable_states:
            pocket = PackagePublishingPocket.BACKPORTS
        else:
            pocket = PackagePublishingPocket.RELEASE
        sourcepackage = branch.sourcepackage
        suite_sourcepackage = sourcepackage.getSuiteSourcePackage(pocket)
        registrant = self.factory.makePerson()
        ubuntu_branches = getUtility(ILaunchpadCelebrities).ubuntu_branches
        run_with_login(
            ubuntu_branches.teamowner,
            ICanHasLinkedBranch(suite_sourcepackage).setBranch,
            branch, registrant)
        source_branch = self.factory.makePackageBranch(
            sourcepackage=branch.sourcepackage)
        proposal = source_branch.addLandingTarget(
            source_branch.registrant, branch)
        package = branch.sourcepackage
        person = self.factory.makePerson()

        # Person is not allowed to edit the branch presently.
        self.assertCannotEdit(person, branch)
        # And so isn't allowed to edit the merge proposal
        self.assertCannotEdit(person, proposal)

        # Now give 'person' permission to upload to 'package'.
        archive = branch.distroseries.distribution.main_archive
        spn = package.sourcepackagename
        self.permission_set.newPackageUploader(archive, person, spn)

        # Now person can edit the branch on the basis of the upload
        # permissions granted above.
        self.assertCanEdit(person, branch)
        # And that means they can edit the proposal too
        self.assertCanEdit(person, proposal)
