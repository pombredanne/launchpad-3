# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for classes that implement IHasBranches."""

__metaclass__ = type

from functools import partial

from lp.code.interfaces.hasbranches import IHasBranches
from lp.services.webapp.interfaces import OAuthPermission
from lp.testing import (
    api_url,
    login_person,
    logout,
    record_two_runs,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount
from lp.testing.pages import webservice_for_person


class TestIHasBranches(TestCaseWithFactory):
    """Test that the correct objects implement the interface."""

    layer = DatabaseFunctionalLayer

    def test_product_implements_hasbranches(self):
        # Products should implement IHasBranches.
        product = self.factory.makeProduct()
        self.assertProvides(product, IHasBranches)

    def test_person_implements_hasbranches(self):
        # People should implement IHasBranches.
        person = self.factory.makePerson()
        self.assertProvides(person, IHasBranches)

    def test_project_implements_hasbranches(self):
        # ProjectGroups should implement IHasBranches.
        project = self.factory.makeProject()
        self.assertProvides(project, IHasBranches)


class TestHasMergeProposalsWebservice(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_constant_query_count(self):
        # Person.getMergeProposals has a constant query count on the
        # webservice.

        # Ensure that both runs fit in a single batch, to avoid needing to
        # account for an extra count query.
        self.pushConfig("launchpad", default_batch_size=10)

        owner = self.factory.makePerson()
        owner_url = api_url(owner)
        webservice = webservice_for_person(
            owner, permission=OAuthPermission.READ_PUBLIC)

        def create_merge_proposal():
            source_branch = self.factory.makeProductBranch(owner=owner)
            self.factory.makeBranchMergeProposal(source_branch=source_branch)
            [source_ref] = self.factory.makeGitRefs(owner=owner)
            self.factory.makeBranchMergeProposalForGit(source_ref=source_ref)

        def get_merge_proposals():
            logout()
            response = webservice.named_get(owner_url, "getMergeProposals")
            self.assertEqual(200, response.status)

        recorder1, recorder2 = record_two_runs(
            get_merge_proposals, create_merge_proposal, 2,
            login_method=partial(login_person, owner), record_request=True)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))
