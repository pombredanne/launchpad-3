# Copyright 2015-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Git repository collections."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
from operator import attrgetter

import pytz
from storm.store import (
    EmptyResultSet,
    Store,
    )
from testtools.matchers import Equals
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import InformationType
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.app.interfaces.services import IService
from lp.code.enums import (
    BranchMergeProposalStatus,
    BranchSubscriptionDiffSize,
    BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel,
    )
from lp.code.interfaces.codehosting import LAUNCHPAD_SERVICES
from lp.code.interfaces.gitcollection import (
    IAllGitRepositories,
    IGitCollection,
    )
from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.code.model.gitcollection import GenericGitCollection
from lp.code.model.gitrepository import GitRepository
from lp.registry.enums import PersonVisibility
from lp.registry.interfaces.person import TeamMembershipPolicy
from lp.registry.model.persondistributionsourcepackage import (
    PersonDistributionSourcePackage,
    )
from lp.registry.model.personproduct import PersonProduct
from lp.services.database.interfaces import IStore
from lp.services.webapp.publisher import canonical_url
from lp.testing import (
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.matchers import HasQueryCount


class TestGitCollectionAdaptation(TestCaseWithFactory):
    """Check that certain objects can be adapted to a Git repository
    collection."""

    layer = DatabaseFunctionalLayer

    def assertCollection(self, target):
        self.assertIsNotNone(IGitCollection(target, None))

    def test_project(self):
        # A project can be adapted to a Git repository collection.
        self.assertCollection(self.factory.makeProduct())

    def test_project_group(self):
        # A project group can be adapted to a Git repository collection.
        self.assertCollection(self.factory.makeProject())

    def test_distribution(self):
        # A distribution can be adapted to a Git repository collection.
        self.assertCollection(self.factory.makeDistribution())

    def test_distribution_source_package(self):
        # A distribution source package can be adapted to a Git repository
        # collection.
        self.assertCollection(self.factory.makeDistributionSourcePackage())

    def test_person(self):
        # A person can be adapted to a Git repository collection.
        self.assertCollection(self.factory.makePerson())

    def test_person_product(self):
        # A PersonProduct can be adapted to a Git repository collection.
        project = self.factory.makeProduct()
        self.assertCollection(PersonProduct(project.owner, project))

    def test_person_distribution_source_package(self):
        # A PersonDistributionSourcePackage can be adapted to a Git
        # repository collection.
        dsp = self.factory.makeDistributionSourcePackage()
        self.assertCollection(
            PersonDistributionSourcePackage(dsp.distribution.owner, dsp))


class TestGenericGitCollection(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGenericGitCollection, self).setUp()
        self.store = IStore(GitRepository)

    def test_provides_gitcollection(self):
        # `GenericGitCollection` provides the `IGitCollection`
        # interface.
        self.assertProvides(GenericGitCollection(self.store), IGitCollection)

    def test_getRepositories_no_filter_no_repositories(self):
        # If no filter is specified, then the collection is of all
        # repositories in Launchpad.  By default, there are no repositories.
        collection = GenericGitCollection(self.store)
        self.assertEqual([], list(collection.getRepositories()))

    def test_getRepositories_no_filter(self):
        # If no filter is specified, then the collection is of all
        # repositories in Launchpad.
        collection = GenericGitCollection(self.store)
        repository = self.factory.makeGitRepository()
        self.assertEqual([repository], list(collection.getRepositories()))

    def test_getRepositories_project_filter(self):
        # If the specified filter is for the repositories of a particular
        # project, then the collection contains only repositories of that
        # project.
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRepository()
        collection = GenericGitCollection(
            self.store, [GitRepository.project == repository.target])
        self.assertEqual([repository], list(collection.getRepositories()))

    def test_getRepositories_caches_viewers(self):
        # getRepositories() caches the user as a known viewer so that
        # repository.visibleByUser() does not have to hit the database.
        collection = GenericGitCollection(self.store)
        owner = self.factory.makePerson()
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(
            owner=owner, target=project,
            information_type=InformationType.USERDATA)
        someone = self.factory.makePerson()
        with person_logged_in(owner):
            getUtility(IService, 'sharing').ensureAccessGrants(
                [someone], owner, gitrepositories=[repository],
                ignore_permissions=True)
        [repository] = list(collection.visibleByUser(
            someone).getRepositories())
        with StormStatementRecorder() as recorder:
            self.assertTrue(repository.visibleByUser(someone))
            self.assertThat(recorder, HasQueryCount(Equals(0)))

    def test_getRepositoryIds(self):
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRepository()
        collection = GenericGitCollection(
            self.store, [GitRepository.project == repository.target])
        self.assertEqual([repository.id], list(collection.getRepositoryIds()))

    def test_count(self):
        # The 'count' property of a collection is the number of elements in
        # the collection.
        collection = GenericGitCollection(self.store)
        self.assertEqual(0, collection.count())
        for i in range(3):
            self.factory.makeGitRepository()
        self.assertEqual(3, collection.count())

    def test_count_respects_filter(self):
        # If a collection is a subset of all possible repositories, then the
        # count will be the size of that subset.  That is, 'count' respects
        # any filters that are applied.
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRepository()
        collection = GenericGitCollection(
            self.store, [GitRepository.project == repository.target])
        self.assertEqual(1, collection.count())


class TestGitCollectionFilters(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.all_repositories = getUtility(IAllGitRepositories)

    def test_order_by_repository_name(self):
        # The result of getRepositories() can be ordered by
        # `GitRepository.name`, no matter what filters are applied.
        aardvark = self.factory.makeProduct(name='aardvark')
        badger = self.factory.makeProduct(name='badger')
        repository_a = self.factory.makeGitRepository(target=aardvark)
        repository_b = self.factory.makeGitRepository(target=badger)
        person = self.factory.makePerson()
        repository_c = self.factory.makeGitRepository(
            owner=person, target=person)
        self.assertEqual(
            sorted([repository_a, repository_b, repository_c]),
            sorted(self.all_repositories.getRepositories()
                 .order_by(GitRepository.name)))

    def test_count_respects_visibleByUser_filter(self):
        # IGitCollection.count() returns the number of repositories that
        # getRepositories() yields, even when the visibleByUser filter is
        # applied.
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRepository(
            information_type=InformationType.USERDATA)
        collection = self.all_repositories.visibleByUser(repository.owner)
        self.assertEqual(1, collection.getRepositories().count())
        self.assertEqual(1, len(list(collection.getRepositories())))
        self.assertEqual(1, collection.count())

    def test_ownedBy(self):
        # 'ownedBy' returns a new collection restricted to repositories
        # owned by the given person.
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRepository()
        collection = self.all_repositories.ownedBy(repository.owner)
        self.assertEqual([repository], list(collection.getRepositories()))

    def test_ownedByTeamMember(self):
        # 'ownedBy' returns a new collection restricted to repositories
        # owned by any team of which the given person is a member.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(members=[person])
        repository = self.factory.makeGitRepository(owner=team)
        self.factory.makeGitRepository()
        collection = self.all_repositories.ownedByTeamMember(person)
        self.assertEqual([repository], list(collection.getRepositories()))

    def test_in_project(self):
        # 'inProject' returns a new collection restricted to repositories in
        # the given project.
        #
        # NOTE: JonathanLange 2009-02-11: Maybe this should be a more
        # generic method called 'onTarget' that takes a person, package or
        # project.
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRepository()
        collection = self.all_repositories.inProject(repository.target)
        self.assertEqual([repository], list(collection.getRepositories()))

    def test_inProjectGroup(self):
        # 'inProjectGroup' returns a new collection restricted to
        # repositories in the given project group.
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRepository()
        projectgroup = self.factory.makeProject()
        removeSecurityProxy(repository.target).projectgroup = projectgroup
        collection = self.all_repositories.inProjectGroup(projectgroup)
        self.assertEqual([repository], list(collection.getRepositories()))

    def test_isExclusive(self):
        # 'isExclusive' is restricted to repositories owned by exclusive
        # teams and users.
        user = self.factory.makePerson()
        team = self.factory.makeTeam(
            membership_policy=TeamMembershipPolicy.RESTRICTED)
        other_team = self.factory.makeTeam(
            membership_policy=TeamMembershipPolicy.OPEN)
        team_repository = self.factory.makeGitRepository(owner=team)
        user_repository = self.factory.makeGitRepository(owner=user)
        self.factory.makeGitRepository(owner=other_team)
        collection = self.all_repositories.isExclusive()
        self.assertContentEqual(
            [team_repository, user_repository],
            list(collection.getRepositories()))

    def test_inProject_and_isExclusive(self):
        # 'inProject' and 'isExclusive' can combine to form a collection
        # that is restricted to repositories of a particular project owned
        # by exclusive teams and users.
        team = self.factory.makeTeam(
            membership_policy=TeamMembershipPolicy.RESTRICTED)
        other_team = self.factory.makeTeam(
            membership_policy=TeamMembershipPolicy.OPEN)
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(target=project, owner=team)
        self.factory.makeGitRepository(owner=team)
        self.factory.makeGitRepository(target=project, owner=other_team)
        collection = self.all_repositories.inProject(project).isExclusive()
        self.assertEqual([repository], list(collection.getRepositories()))
        collection = self.all_repositories.isExclusive().inProject(project)
        self.assertEqual([repository], list(collection.getRepositories()))

    def test_ownedBy_and_inProject(self):
        # 'ownedBy' and 'inProject' can combine to form a collection that is
        # restricted to repositories of a particular project owned by a
        # particular person.
        person = self.factory.makePerson()
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(
            target=project, owner=person)
        self.factory.makeGitRepository(owner=person)
        self.factory.makeGitRepository(target=project)
        collection = self.all_repositories.inProject(project).ownedBy(person)
        self.assertEqual([repository], list(collection.getRepositories()))
        collection = self.all_repositories.ownedBy(person).inProject(project)
        self.assertEqual([repository], list(collection.getRepositories()))

    def test_ownedBy_and_isPrivate(self):
        # 'ownedBy' and 'isPrivate' can combine to form a collection that is
        # restricted to private repositories owned by a particular person.
        person = self.factory.makePerson()
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(
            target=project, owner=person,
            information_type=InformationType.USERDATA)
        self.factory.makeGitRepository(owner=person)
        self.factory.makeGitRepository(target=project)
        collection = self.all_repositories.isPrivate().ownedBy(person)
        self.assertEqual([repository], list(collection.getRepositories()))
        collection = self.all_repositories.ownedBy(person).isPrivate()
        self.assertEqual([repository], list(collection.getRepositories()))

    def test_ownedByTeamMember_and_inProject(self):
        # 'ownedBy' and 'inProject' can combine to form a collection that is
        # restricted to repositories of a particular project owned by a
        # particular person or team of which the person is a member.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(members=[person])
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(
            target=project, owner=person)
        repository2 = self.factory.makeGitRepository(
            target=project, owner=team)
        self.factory.makeGitRepository(owner=person)
        self.factory.makeGitRepository(target=project)
        project_repositories = self.all_repositories.inProject(project)
        collection = project_repositories.ownedByTeamMember(person)
        self.assertContentEqual(
            [repository, repository2], collection.getRepositories())
        person_repositories = self.all_repositories.ownedByTeamMember(person)
        collection = person_repositories.inProject(project)
        self.assertContentEqual(
            [repository, repository2], collection.getRepositories())

    def test_in_distribution(self):
        # 'inDistribution' returns a new collection that only has
        # repositories that are package repositories associated with the
        # distribution specified.
        distro = self.factory.makeDistribution()
        # Make two repositories in the same distribution, but different
        # source packages.
        dsp = self.factory.makeDistributionSourcePackage(distribution=distro)
        repository = self.factory.makeGitRepository(target=dsp)
        dsp2 = self.factory.makeDistributionSourcePackage(distribution=distro)
        repository2 = self.factory.makeGitRepository(target=dsp2)
        # Another repository in a different distribution.
        self.factory.makeGitRepository(
            target=self.factory.makeDistributionSourcePackage())
        # And a project repository.
        self.factory.makeGitRepository()
        collection = self.all_repositories.inDistribution(distro)
        self.assertEqual(
            sorted([repository, repository2]),
            sorted(collection.getRepositories()))

    def test_in_distribution_source_package(self):
        # 'inDistributionSourcePackage' returns a new collection that only
        # has repositories for the source package in the distribution.
        distro = self.factory.makeDistribution()
        dsp = self.factory.makeDistributionSourcePackage(distribution=distro)
        dsp_other_distro = self.factory.makeDistributionSourcePackage()
        repository = self.factory.makeGitRepository(target=dsp)
        repository2 = self.factory.makeGitRepository(target=dsp)
        self.factory.makeGitRepository(target=dsp_other_distro)
        self.factory.makeGitRepository()
        collection = self.all_repositories.inDistributionSourcePackage(dsp)
        self.assertEqual(
            sorted([repository, repository2]),
            sorted(collection.getRepositories()))

    def test_withIds(self):
        # 'withIds' returns a new collection that only has repositories with
        # the given ids.
        repository1 = self.factory.makeGitRepository()
        repository2 = self.factory.makeGitRepository()
        self.factory.makeGitRepository()
        ids = [repository1.id, repository2.id]
        collection = self.all_repositories.withIds(*ids)
        self.assertEqual(
            sorted([repository1, repository2]),
            sorted(collection.getRepositories()))

    def test_registeredBy(self):
        # 'registeredBy' returns a new collection that only has repositories
        # that were registered by the given user.
        registrant = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            owner=registrant, registrant=registrant)
        removeSecurityProxy(repository).owner = self.factory.makePerson()
        self.factory.makeGitRepository()
        collection = self.all_repositories.registeredBy(registrant)
        self.assertEqual([repository], list(collection.getRepositories()))

    def test_subscribedBy(self):
        # 'subscribedBy' returns a new collection that only has repositories
        # that the given user is subscribed to.
        repository = self.factory.makeGitRepository()
        subscriber = self.factory.makePerson()
        repository.subscribe(
            subscriber, BranchSubscriptionNotificationLevel.NOEMAIL,
            BranchSubscriptionDiffSize.NODIFF,
            CodeReviewNotificationLevel.NOEMAIL,
            subscriber)
        collection = self.all_repositories.subscribedBy(subscriber)
        self.assertEqual([repository], list(collection.getRepositories()))

    def test_targetedBy(self):
        # Only repositories that are merge targets are returned.
        [target_ref] = self.factory.makeGitRefs()
        registrant = self.factory.makePerson()
        self.factory.makeBranchMergeProposalForGit(
            target_ref=target_ref, registrant=registrant)
        # And another not registered by registrant.
        self.factory.makeBranchMergeProposalForGit()
        collection = self.all_repositories.targetedBy(registrant)
        self.assertEqual(
            [target_ref.repository], list(collection.getRepositories()))

    def test_targetedBy_since(self):
        # Ignore proposals created before 'since'.
        bmp = self.factory.makeBranchMergeProposalForGit()
        date_created = self.factory.getUniqueDate()
        removeSecurityProxy(bmp).date_created = date_created
        registrant = bmp.registrant
        repositories = self.all_repositories.targetedBy(
            registrant, since=date_created)
        self.assertEqual(
            [bmp.target_git_repository], list(repositories.getRepositories()))
        since = self.factory.getUniqueDate()
        repositories = self.all_repositories.targetedBy(
            registrant, since=since)
        self.assertEqual([], list(repositories.getRepositories()))


class TestBranchMergeProposals(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.all_repositories = getUtility(IAllGitRepositories)

    def test_empty_branch_merge_proposals(self):
        proposals = self.all_repositories.getMergeProposals()
        self.assertEqual([], list(proposals))

    def test_empty_revisions_shortcut(self):
        # If you explicitly pass an empty collection of revision numbers,
        # the method shortcuts and gives you an empty result set.  In this
        # way, merged_revnos=None (the default) has a very different behaviour
        # than merged_revnos=[]: the first is no restriction, while the second
        # excludes everything.
        self.factory.makeBranchMergeProposalForGit()
        proposals = self.all_repositories.getMergeProposals(
            merged_revision_ids=[])
        self.assertEqual([], list(proposals))
        self.assertIsInstance(proposals, EmptyResultSet)

    def test_some_branch_merge_proposals(self):
        mp = self.factory.makeBranchMergeProposalForGit()
        proposals = self.all_repositories.getMergeProposals()
        self.assertEqual([mp], list(proposals))

    def test_just_owned_branch_merge_proposals(self):
        # If the collection only includes branches owned by a person, the
        # getMergeProposals() will only return merge proposals for source
        # branches that are owned by that person.
        person = self.factory.makePerson()
        project = self.factory.makeProduct()
        [ref1] = self.factory.makeGitRefs(target=project, owner=person)
        [ref2] = self.factory.makeGitRefs(target=project, owner=person)
        [ref3] = self.factory.makeGitRefs(target=project)
        self.factory.makeGitRefs(target=project)
        [target] = self.factory.makeGitRefs(target=project)
        mp1 = self.factory.makeBranchMergeProposalForGit(
            target_ref=target, source_ref=ref1)
        mp2 = self.factory.makeBranchMergeProposalForGit(
            target_ref=target, source_ref=ref2)
        self.factory.makeBranchMergeProposalForGit(
            target_ref=target, source_ref=ref3)
        collection = self.all_repositories.ownedBy(person)
        proposals = collection.getMergeProposals()
        self.assertEqual(sorted([mp1, mp2]), sorted(proposals))

    def test_preloading_for_previewdiff(self):
        project = self.factory.makeProduct()
        [target] = self.factory.makeGitRefs(target=project)
        owner = self.factory.makePerson()
        [ref1] = self.factory.makeGitRefs(target=project, owner=owner)
        [ref2] = self.factory.makeGitRefs(target=project, owner=owner)
        bmp1 = self.factory.makeBranchMergeProposalForGit(
            target_ref=target, source_ref=ref1)
        bmp2 = self.factory.makeBranchMergeProposalForGit(
            target_ref=target, source_ref=ref2)
        old_date = datetime.now(pytz.UTC) - timedelta(hours=1)
        self.factory.makePreviewDiff(
            merge_proposal=bmp1, date_created=old_date)
        previewdiff1 = self.factory.makePreviewDiff(merge_proposal=bmp1)
        self.factory.makePreviewDiff(
            merge_proposal=bmp2, date_created=old_date)
        previewdiff2 = self.factory.makePreviewDiff(merge_proposal=bmp2)
        Store.of(bmp1).flush()
        Store.of(bmp1).invalidate()
        collection = self.all_repositories.ownedBy(owner)
        [pre_bmp1, pre_bmp2] = sorted(
            collection.getMergeProposals(eager_load=True),
            key=attrgetter('id'))
        with StormStatementRecorder() as recorder:
            self.assertEqual(
                removeSecurityProxy(pre_bmp1.preview_diff).id, previewdiff1.id)
            self.assertEqual(
                removeSecurityProxy(pre_bmp2.preview_diff).id, previewdiff2.id)
        self.assertThat(recorder, HasQueryCount(Equals(0)))

    def test_merge_proposals_in_project(self):
        mp1 = self.factory.makeBranchMergeProposalForGit()
        self.factory.makeBranchMergeProposalForGit()
        project = mp1.source_git_ref.target
        collection = self.all_repositories.inProject(project)
        proposals = collection.getMergeProposals()
        self.assertEqual([mp1], list(proposals))

    def test_merge_proposals_by_id(self):
        # merge_proposal_ids limits the returned merge proposals by ID.
        [target] = self.factory.makeGitRefs()
        mp1 = self.factory.makeBranchMergeProposalForGit(target_ref=target)
        mp2 = self.factory.makeBranchMergeProposalForGit(target_ref=target)
        self.factory.makeBranchMergeProposalForGit(target_ref=target)
        result = self.all_repositories.getMergeProposals(
            target_repository=target.repository, target_path=target.path,
            merge_proposal_ids=[mp1.id, mp2.id])
        self.assertContentEqual([mp1, mp2], result)
        result = self.all_repositories.getMergeProposals(
            target_repository=target.repository, target_path=target.path,
            merge_proposal_ids=[])
        self.assertContentEqual([], result)

    def test_target_branch_private(self):
        # The target branch must be in the branch collection, as must the
        # source branch.
        registrant = self.factory.makePerson()
        mp1 = self.factory.makeBranchMergeProposalForGit(registrant=registrant)
        naked_repository = removeSecurityProxy(mp1.target_git_repository)
        naked_repository.transitionToInformationType(
            InformationType.USERDATA, registrant, verify_policy=False)
        collection = self.all_repositories.visibleByUser(None)
        proposals = collection.getMergeProposals()
        self.assertEqual([], list(proposals))

    def test_status_restriction(self):
        mp1 = self.factory.makeBranchMergeProposalForGit(
            set_state=BranchMergeProposalStatus.WORK_IN_PROGRESS)
        mp2 = self.factory.makeBranchMergeProposalForGit(
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW)
        self.factory.makeBranchMergeProposalForGit(
            set_state=BranchMergeProposalStatus.CODE_APPROVED)
        proposals = self.all_repositories.getMergeProposals(
            [BranchMergeProposalStatus.WORK_IN_PROGRESS,
             BranchMergeProposalStatus.NEEDS_REVIEW])
        self.assertEqual(sorted([mp1, mp2]), sorted(proposals))

    def test_status_restriction_with_project_filter(self):
        # getMergeProposals returns the merge proposals with a particular
        # status that are _inside_ the repository collection.  mp1 is in the
        # product with NEEDS_REVIEW, mp2 is outside of the project and mp3
        # has an excluded status.
        mp1 = self.factory.makeBranchMergeProposalForGit(
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW)
        self.factory.makeBranchMergeProposalForGit(
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW)
        project = mp1.source_git_ref.target
        [ref1] = self.factory.makeGitRefs(target=project)
        [ref2] = self.factory.makeGitRefs(target=project)
        self.factory.makeBranchMergeProposalForGit(
            target_ref=ref1, source_ref=ref2,
            set_state=BranchMergeProposalStatus.CODE_APPROVED)
        collection = self.all_repositories.inProject(project)
        proposals = collection.getMergeProposals(
            [BranchMergeProposalStatus.NEEDS_REVIEW])
        self.assertEqual([mp1], list(proposals))

    def test_specifying_target_repository(self):
        # If the target_repository is specified but not the target_path,
        # only merge proposals where that repository is the target are
        # returned.
        [ref1, ref2] = self.factory.makeGitRefs(
            paths=["refs/heads/ref1", "refs/heads/ref2"])
        mp1 = self.factory.makeBranchMergeProposalForGit(target_ref=ref1)
        mp2 = self.factory.makeBranchMergeProposalForGit(target_ref=ref2)
        self.factory.makeBranchMergeProposalForGit()
        proposals = self.all_repositories.getMergeProposals(
            target_repository=mp1.target_git_repository)
        self.assertEqual(sorted([mp1, mp2]), sorted(proposals))

    def test_specifying_target_ref(self):
        # If the target_repository and target_path are specified, only merge
        # proposals where that ref is the target are returned.
        mp1 = self.factory.makeBranchMergeProposalForGit()
        self.factory.makeBranchMergeProposalForGit()
        proposals = self.all_repositories.getMergeProposals(
            target_repository=mp1.target_git_repository,
            target_path=mp1.target_git_path)
        self.assertEqual([mp1], list(proposals))

    def test_specifying_prerequisite_repository(self):
        # If the prerequisite_repository is specified but not the
        # prerequisite_path, only merge proposals where that repository is
        # the prerequisite are returned.
        [ref1, ref2] = self.factory.makeGitRefs(
            paths=["refs/heads/ref1", "refs/heads/ref2"])
        mp1 = self.factory.makeBranchMergeProposalForGit(prerequisite_ref=ref1)
        mp2 = self.factory.makeBranchMergeProposalForGit(prerequisite_ref=ref2)
        self.factory.makeBranchMergeProposalForGit()
        proposals = self.all_repositories.getMergeProposals(
            prerequisite_repository=ref1.repository)
        self.assertEqual(sorted([mp1, mp2]), sorted(proposals))

    def test_specifying_prerequisite_ref(self):
        # If the prerequisite_repository and prerequisite_path are
        # specified, only merge proposals where that ref is the prerequisite
        # are returned.
        [prerequisite] = self.factory.makeGitRefs()
        mp1 = self.factory.makeBranchMergeProposalForGit(
            prerequisite_ref=prerequisite)
        self.factory.makeBranchMergeProposalForGit()
        proposals = self.all_repositories.getMergeProposals(
            prerequisite_repository=prerequisite.repository,
            prerequisite_path=prerequisite.path)
        self.assertEqual([mp1], list(proposals))


class TestBranchMergeProposalsForReviewer(TestCaseWithFactory):
    """Tests for IGitCollection.getProposalsForReviewer()."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Use the admin user as we don't care about who can and can't call
        # nominate reviewer in this test.
        TestCaseWithFactory.setUp(self, 'admin@canonical.com')
        self.all_repositories = getUtility(IAllGitRepositories)

    def test_getProposalsForReviewer(self):
        reviewer = self.factory.makePerson()
        proposal = self.factory.makeBranchMergeProposalForGit()
        proposal.nominateReviewer(reviewer, reviewer)
        self.factory.makeBranchMergeProposalForGit()
        proposals = self.all_repositories.getMergeProposalsForReviewer(
            reviewer)
        self.assertEqual([proposal], list(proposals))

    def test_getProposalsForReviewer_filter_status(self):
        reviewer = self.factory.makePerson()
        proposal1 = self.factory.makeBranchMergeProposalForGit(
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW)
        proposal1.nominateReviewer(reviewer, reviewer)
        proposal2 = self.factory.makeBranchMergeProposalForGit(
            set_state=BranchMergeProposalStatus.WORK_IN_PROGRESS)
        proposal2.nominateReviewer(reviewer, reviewer)
        proposals = self.all_repositories.getMergeProposalsForReviewer(
            reviewer, [BranchMergeProposalStatus.NEEDS_REVIEW])
        self.assertEqual([proposal1], list(proposals))

    def test_getProposalsForReviewer_anonymous(self):
        # Don't include proposals if the target branch is private for
        # anonymous views.
        reviewer = self.factory.makePerson()
        [target_ref] = self.factory.makeGitRefs(
            information_type=InformationType.USERDATA)
        proposal = self.factory.makeBranchMergeProposalForGit(
            target_ref=target_ref)
        proposal.nominateReviewer(reviewer, reviewer)
        proposals = self.all_repositories.visibleByUser(
            None).getMergeProposalsForReviewer(reviewer)
        self.assertEqual([], list(proposals))

    def test_getProposalsForReviewer_anonymous_source_private(self):
        # Don't include proposals if the source branch is private for
        # anonymous views.
        reviewer = self.factory.makePerson()
        project = self.factory.makeProduct()
        [source_ref] = self.factory.makeGitRefs(
            target=project, information_type=InformationType.USERDATA)
        [target_ref] = self.factory.makeGitRefs(target=project)
        proposal = self.factory.makeBranchMergeProposalForGit(
            source_ref=source_ref, target_ref=target_ref)
        proposal.nominateReviewer(reviewer, reviewer)
        proposals = self.all_repositories.visibleByUser(
            None).getMergeProposalsForReviewer(reviewer)
        self.assertEqual([], list(proposals))

    def test_getProposalsForReviewer_for_product(self):
        reviewer = self.factory.makePerson()
        proposal = self.factory.makeBranchMergeProposalForGit()
        proposal.nominateReviewer(reviewer, reviewer)
        proposal2 = self.factory.makeBranchMergeProposalForGit()
        proposal2.nominateReviewer(reviewer, reviewer)
        proposals = self.all_repositories.inProject(
            proposal.merge_source.target).getMergeProposalsForReviewer(
            reviewer)
        self.assertEqual([proposal], list(proposals))


class TestGenericGitCollectionVisibleFilter(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.public_repository = self.factory.makeGitRepository(name='public')
        self.private_repository = self.factory.makeGitRepository(
            name='private', information_type=InformationType.USERDATA)
        self.all_repositories = getUtility(IAllGitRepositories)

    def test_all_repositories(self):
        # Without the visibleByUser filter, all repositories are in the
        # collection.
        self.assertEqual(
            sorted([self.public_repository, self.private_repository]),
            sorted(self.all_repositories.getRepositories()))

    def test_anonymous_sees_only_public(self):
        # Anonymous users can see only public repositories.
        repositories = self.all_repositories.visibleByUser(None)
        self.assertEqual(
            [self.public_repository], list(repositories.getRepositories()))

    def test_visibility_then_project(self):
        # We can apply other filters after applying the visibleByUser filter.
        # Create another public repository.
        self.factory.makeGitRepository()
        repositories = self.all_repositories.visibleByUser(None).inProject(
            self.public_repository.target).getRepositories()
        self.assertEqual([self.public_repository], list(repositories))

    def test_random_person_sees_only_public(self):
        # Logged in users with no special permissions can see only public
        # repositories.
        person = self.factory.makePerson()
        repositories = self.all_repositories.visibleByUser(person)
        self.assertEqual(
            [self.public_repository], list(repositories.getRepositories()))

    def test_owner_sees_own_repositories(self):
        # Users can always see the repositories that they own, as well as
        # public repositories.
        owner = removeSecurityProxy(self.private_repository).owner
        repositories = self.all_repositories.visibleByUser(owner)
        self.assertEqual(
            sorted([self.public_repository, self.private_repository]),
            sorted(repositories.getRepositories()))

    def test_launchpad_services_sees_all(self):
        # The LAUNCHPAD_SERVICES special user sees *everything*.
        repositories = self.all_repositories.visibleByUser(LAUNCHPAD_SERVICES)
        self.assertEqual(
            sorted(self.all_repositories.getRepositories()),
            sorted(repositories.getRepositories()))

    def test_admins_see_all(self):
        # Launchpad administrators see *everything*.
        admin = self.factory.makePerson()
        admin_team = removeSecurityProxy(
            getUtility(ILaunchpadCelebrities).admin)
        admin_team.addMember(admin, admin_team.teamowner)
        repositories = self.all_repositories.visibleByUser(admin)
        self.assertEqual(
            sorted(self.all_repositories.getRepositories()),
            sorted(repositories.getRepositories()))

    def test_subscribers_can_see_repositories(self):
        # A person subscribed to a repository can see it, even if it's
        # private.
        subscriber = self.factory.makePerson()
        removeSecurityProxy(self.private_repository).subscribe(
            subscriber, BranchSubscriptionNotificationLevel.NOEMAIL,
            BranchSubscriptionDiffSize.NODIFF,
            CodeReviewNotificationLevel.NOEMAIL,
            subscriber)
        repositories = self.all_repositories.visibleByUser(subscriber)
        self.assertEqual(
            sorted([self.public_repository, self.private_repository]),
            sorted(repositories.getRepositories()))

    def test_subscribed_team_members_can_see_repositories(self):
        # A person in a team that is subscribed to a repository can see that
        # repository, even if it's private.
        team_owner = self.factory.makePerson()
        team = self.factory.makeTeam(
            membership_policy=TeamMembershipPolicy.MODERATED,
            owner=team_owner)
        # Subscribe the team.
        removeSecurityProxy(self.private_repository).subscribe(
            team, BranchSubscriptionNotificationLevel.NOEMAIL,
            BranchSubscriptionDiffSize.NODIFF,
            CodeReviewNotificationLevel.NOEMAIL,
            team_owner)
        # Members of the team can see the private repository that the team
        # is subscribed to.
        repositories = self.all_repositories.visibleByUser(team_owner)
        self.assertEqual(
            sorted([self.public_repository, self.private_repository]),
            sorted(repositories.getRepositories()))

    def test_private_teams_see_own_private_personal_repositories(self):
        # Private teams are given an access grant to see their private
        # personal repositories.
        team_owner = self.factory.makePerson()
        team = self.factory.makeTeam(
            visibility=PersonVisibility.PRIVATE,
            membership_policy=TeamMembershipPolicy.MODERATED,
            owner=team_owner)
        with person_logged_in(team_owner):
            personal_repository = self.factory.makeGitRepository(
                owner=team, target=team,
                information_type=InformationType.USERDATA)
            # The team is automatically subscribed to the repository since
            # they are the owner.  We want to unsubscribe them so that they
            # lose access conferred via subscription and rely instead on the
            # APG.
            personal_repository.unsubscribe(team, team_owner, True)
            # Make another personal repository the team can't see.
            other_person = self.factory.makePerson()
            self.factory.makeGitRepository(
                owner=other_person, target=other_person,
                information_type=InformationType.USERDATA)
            repositories = self.all_repositories.visibleByUser(team)
        self.assertEqual(
            sorted([self.public_repository, personal_repository]),
            sorted(repositories.getRepositories()))


class TestSearch(TestCaseWithFactory):
    """Tests for IGitCollection.search()."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.collection = getUtility(IAllGitRepositories)

    def test_exact_match_unique_name(self):
        # If you search for a unique name of a repository that exists,
        # you'll get a single result with a repository with that repository
        # name.
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRepository()
        search_results = self.collection.search(repository.unique_name)
        self.assertEqual([repository], list(search_results))

    def test_unique_name_match_not_in_collection(self):
        # If you search for a unique name of a repository that does not
        # exist, you'll get an empty result set.
        repository = self.factory.makeGitRepository()
        collection = self.collection.inProject(self.factory.makeProduct())
        search_results = collection.search(repository.unique_name)
        self.assertEqual([], list(search_results))

    def test_exact_match_launchpad_url(self):
        # If you search for the Launchpad URL of a repository, and there is
        # a repository with that URL, then you get a single result with that
        # repository.
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRepository()
        search_results = self.collection.search(repository.getCodebrowseUrl())
        self.assertEqual([repository], list(search_results))

    def test_exact_match_with_lp_colon_url(self):
        repository = self.factory.makeGitRepository()
        lp_name = 'lp:' + repository.unique_name
        search_results = self.collection.search(lp_name)
        self.assertEqual([repository], list(search_results))

    def test_exact_match_full_url(self):
        repository = self.factory.makeGitRepository()
        url = canonical_url(repository)
        self.assertEqual([repository], list(self.collection.search(url)))

    def test_exact_match_bad_url(self):
        search_results = self.collection.search('http:hahafail')
        self.assertEqual([], list(search_results))

    def test_exact_match_git_identity(self):
        # If you search for the Git identity of a repository, then you get a
        # single result with that repository.
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRepository()
        search_results = self.collection.search(repository.git_identity)
        self.assertEqual([repository], list(search_results))

    def test_exact_match_git_identity_development_focus(self):
        # If you search for the development focus and it is set, you get a
        # single result with the development focus repository.
        fooix = self.factory.makeProduct(name='fooix')
        repository = self.factory.makeGitRepository(
            owner=fooix.owner, target=fooix)
        with person_logged_in(fooix.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                fooix, repository)
        self.factory.makeGitRepository()
        search_results = self.collection.search('lp:fooix')
        self.assertEqual([repository], list(search_results))

    def test_bad_match_git_identity_development_focus(self):
        # If you search for the development focus for a project where one
        # isn't set, you get an empty search result.
        fooix = self.factory.makeProduct(name='fooix')
        self.factory.makeGitRepository(target=fooix)
        self.factory.makeGitRepository()
        search_results = self.collection.search('lp:fooix')
        self.assertEqual([], list(search_results))

    def test_bad_match_git_identity_no_project(self):
        # If you search for the development focus for a project where one
        # isn't set, you get an empty search result.
        self.factory.makeGitRepository()
        search_results = self.collection.search('lp:fooix')
        self.assertEqual([], list(search_results))

    def test_exact_match_url_trailing_slash(self):
        # Sometimes, users are inconsiderately unaware of our arbitrary
        # database restrictions and will put trailing slashes on their
        # search queries.  Rather bravely, we refuse to explode in this
        # case.
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRepository()
        search_results = self.collection.search(
            repository.getCodebrowseUrl() + '/')
        self.assertEqual([repository], list(search_results))

    def test_match_exact_repository_name(self):
        # search returns all repositories with the same name as the search
        # term.
        repository1 = self.factory.makeGitRepository(name='foo')
        repository2 = self.factory.makeGitRepository(name='foo')
        self.factory.makeGitRepository()
        search_results = self.collection.search('foo')
        self.assertEqual(
            sorted([repository1, repository2]), sorted(search_results))

    def disabled_test_match_against_unique_name(self):
        # XXX cjwatson 2015-02-06: Disabled until the URL format settles
        # down.
        repository = self.factory.makeGitRepository(name='fooa')
        search_term = repository.target.name + '/foo'
        search_results = self.collection.search(search_term)
        self.assertEqual([repository], list(search_results))

    def test_match_sub_repository_name(self):
        # search returns all repositories which have a name of which the
        # search term is a substring.
        repository1 = self.factory.makeGitRepository(name='afoo')
        repository2 = self.factory.makeGitRepository(name='foob')
        self.factory.makeGitRepository()
        search_results = self.collection.search('foo')
        self.assertEqual(
            sorted([repository1, repository2]), sorted(search_results))

    def test_match_ignores_case(self):
        repository = self.factory.makeGitRepository(name='foobar')
        search_results = self.collection.search('FOOBAR')
        self.assertEqual([repository], list(search_results))

    def test_dont_match_project_if_in_project(self):
        # If the container is restricted to the project, then we don't match
        # the project name.
        project = self.factory.makeProduct('foo')
        repository1 = self.factory.makeGitRepository(
            target=project, name='foo')
        self.factory.makeGitRepository(target=project, name='bar')
        search_results = self.collection.inProject(project).search('foo')
        self.assertEqual([repository1], list(search_results))


class TestGetTeamsWithRepositories(TestCaseWithFactory):
    """Test the IGitCollection.getTeamsWithRepositories method."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.all_repositories = getUtility(IAllGitRepositories)

    def test_no_teams(self):
        # If the user is not a member of any teams, there are no results,
        # even if the person owns a repository themselves.
        person = self.factory.makePerson()
        self.factory.makeGitRepository(owner=person)
        teams = list(self.all_repositories.getTeamsWithRepositories(person))
        self.assertEqual([], teams)

    def test_team_repositories(self):
        # Return the teams that the user is in and that have repositories.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(owner=person)
        self.factory.makeGitRepository(owner=team)
        # Make another team that person is in that has no repositories.
        self.factory.makeTeam(owner=person)
        teams = list(self.all_repositories.getTeamsWithRepositories(person))
        self.assertEqual([team], teams)

    def test_respects_restrictions(self):
        # Create a team with repositories on a project, and another
        # repository in a different namespace owned by a different team that
        # the person is a member of.  Restricting the collection will return
        # just the teams that have repositories in that restricted
        # collection.
        person = self.factory.makePerson()
        team1 = self.factory.makeTeam(owner=person)
        repository = self.factory.makeGitRepository(owner=team1)
        # Make another team that person is in that owns a repository in a
        # different namespace to the namespace of the repository owned by
        # team1.
        team2 = self.factory.makeTeam(owner=person)
        self.factory.makeGitRepository(owner=team2)
        collection = self.all_repositories.inProject(repository.target)
        teams = list(collection.getTeamsWithRepositories(person))
        self.assertEqual([team1], teams)


class TestGitCollectionOwnerCounts(TestCaseWithFactory):
    """Test IGitCollection.ownerCounts."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.all_repositories = getUtility(IAllGitRepositories)

    def test_no_repositories(self):
        # If there are no repositories, we should get zero counts for both.
        person_count, team_count = self.all_repositories.ownerCounts()
        self.assertEqual(0, person_count)
        self.assertEqual(0, team_count)

    def test_individual_repository_owners(self):
        # Repositories owned by an individual are returned as the first part
        # of the tuple.
        self.factory.makeGitRepository()
        self.factory.makeGitRepository()
        person_count, team_count = self.all_repositories.ownerCounts()
        self.assertEqual(2, person_count)
        self.assertEqual(0, team_count)

    def test_team_repository_owners(self):
        # Repositories owned by teams are returned as the second part of the
        # tuple.
        self.factory.makeGitRepository(owner=self.factory.makeTeam())
        self.factory.makeGitRepository(owner=self.factory.makeTeam())
        person_count, team_count = self.all_repositories.ownerCounts()
        self.assertEqual(0, person_count)
        self.assertEqual(2, team_count)

    def test_multiple_repositories_owned_counted_once(self):
        # Confirming that a person that owns multiple repositories only gets
        # counted once.
        individual = self.factory.makePerson()
        team = self.factory.makeTeam()
        for owner in [individual, individual, team, team]:
            self.factory.makeGitRepository(owner=owner)
        person_count, team_count = self.all_repositories.ownerCounts()
        self.assertEqual(1, person_count)
        self.assertEqual(1, team_count)

    def test_counts_limited_by_collection(self):
        # For collections that are constrained in some way, we only get
        # counts for the constrained collection.
        r1 = self.factory.makeGitRepository()
        project = r1.target
        self.factory.makeGitRepository()
        collection = self.all_repositories.inProject(project)
        person_count, team_count = collection.ownerCounts()
        self.assertEqual(1, person_count)
