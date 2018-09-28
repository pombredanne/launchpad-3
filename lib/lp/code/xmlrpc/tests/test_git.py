# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the internal Git API."""

__metaclass__ = type

from pymacaroons import Macaroon
from testtools.matchers import (
    Equals,
    MatchesListwise,
    MatchesDict,
    )
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import InformationType
from lp.code.enums import (
    GitRepositoryType,
    TargetRevisionControlSystems,
    )
from lp.code.errors import GitRepositoryCreationFault
from lp.code.interfaces.codeimportjob import ICodeImportJobWorkflow
from lp.code.interfaces.gitcollection import IAllGitRepositories
from lp.code.interfaces.gitjob import IGitRefScanJobSource
from lp.code.interfaces.gitrepository import (
    GIT_REPOSITORY_NAME_VALIDATION_ERROR_MESSAGE,
    IGitRepositorySet,
    )
from lp.code.tests.helpers import GitHostingFixture
from lp.code.xmlrpc.git import GitAPI
from lp.registry.enums import TeamMembershipPolicy
from lp.services.config import config
from lp.services.macaroons.interfaces import IMacaroonIssuer
from lp.services.webapp.escaping import html_escape
from lp.testing import (
    admin_logged_in,
    ANONYMOUS,
    celebrity_logged_in,
    login,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    AppServerLayer,
    LaunchpadFunctionalLayer,
    )
from lp.xmlrpc import faults


class TestGitAPIMixin:
    """Helper methods for `IGitAPI` tests, and security-relevant tests."""

    def setUp(self):
        super(TestGitAPIMixin, self).setUp()
        self.git_api = GitAPI(None, None)
        self.hosting_fixture = self.useFixture(GitHostingFixture())
        self.repository_set = getUtility(IGitRepositorySet)

    def assertGitRepositoryNotFound(self, requester, path, permission="read",
                                    can_authenticate=False, macaroon_raw=None):
        """Assert that the given path cannot be translated."""
        if requester is not None:
            requester = requester.id
        auth_params = {"uid": requester, "can-authenticate": can_authenticate}
        if macaroon_raw is not None:
            auth_params["macaroon"] = macaroon_raw
        fault = self.git_api.translatePath(path, permission, auth_params)
        self.assertEqual(
            faults.GitRepositoryNotFound(path.strip("/")), fault)

    def assertPermissionDenied(self, requester, path,
                               message="Permission denied.",
                               permission="read", can_authenticate=False,
                               macaroon_raw=None):
        """Assert that looking at the given path returns PermissionDenied."""
        if requester is not None:
            requester = requester.id
        auth_params = {"uid": requester, "can-authenticate": can_authenticate}
        if macaroon_raw is not None:
            auth_params["macaroon"] = macaroon_raw
        fault = self.git_api.translatePath(path, permission, auth_params)
        self.assertEqual(faults.PermissionDenied(message), fault)

    def assertUnauthorized(self, requester, path,
                           message="Authorisation required.",
                           permission="read", can_authenticate=False):
        """Assert that looking at the given path returns Unauthorized."""
        if requester is not None:
            requester = requester.id
        fault = self.git_api.translatePath(
            path, permission,
            {"uid": requester, "can-authenticate": can_authenticate})
        self.assertEqual(faults.Unauthorized(message), fault)

    def assertNotFound(self, requester, path, message, permission="read",
                       can_authenticate=False):
        """Assert that looking at the given path returns NotFound."""
        if requester is not None:
            requester = requester.id
        fault = self.git_api.translatePath(
            path, permission,
            {"uid": requester, "can-authenticate": can_authenticate})
        self.assertEqual(faults.NotFound(message), fault)

    def assertInvalidSourcePackageName(self, requester, path, name,
                                       permission="read",
                                       can_authenticate=False):
        """Assert that looking at the given path returns
        InvalidSourcePackageName."""
        if requester is not None:
            requester = requester.id
        fault = self.git_api.translatePath(
            path, permission,
            {"uid": requester, "can-authenticate": can_authenticate})
        self.assertEqual(faults.InvalidSourcePackageName(name), fault)

    def assertInvalidBranchName(self, requester, path, message,
                                permission="read", can_authenticate=False):
        """Assert that looking at the given path returns InvalidBranchName."""
        if requester is not None:
            requester = requester.id
        fault = self.git_api.translatePath(
            path, permission,
            {"uid": requester, "can-authenticate": can_authenticate})
        self.assertEqual(faults.InvalidBranchName(Exception(message)), fault)

    def assertOopsOccurred(self, requester, path,
                           permission="read", can_authenticate=False):
        """Assert that looking at the given path OOPSes."""
        if requester is not None:
            requester = requester.id
        fault = self.git_api.translatePath(
            path, permission,
            {"uid": requester, "can-authenticate": can_authenticate})
        self.assertIsInstance(fault, faults.OopsOccurred)
        prefix = (
            "An unexpected error has occurred while creating a Git "
            "repository. Please report a Launchpad bug and quote: ")
        self.assertStartsWith(fault.faultString, prefix)
        return fault.faultString[len(prefix):].rstrip(".")

    def assertTranslates(self, requester, path, repository, writable,
                         permission="read", can_authenticate=False,
                         macaroon_raw=None, trailing="", private=False):
        if requester is not None:
            requester = requester.id
        auth_params = {"uid": requester, "can-authenticate": can_authenticate}
        if macaroon_raw is not None:
            auth_params["macaroon"] = macaroon_raw
        translation = self.git_api.translatePath(path, permission, auth_params)
        login(ANONYMOUS)
        self.assertEqual(
            {"path": removeSecurityProxy(repository).getInternalPath(),
             "writable": writable, "trailing": trailing, "private": private},
            translation)

    def assertCreates(self, requester, path, can_authenticate=False,
                      private=False):
        if requester is None:
            requester_id = requester
        else:
            requester_id = requester.id
        translation = self.git_api.translatePath(
            path, "write",
            {"uid": requester_id, "can-authenticate": can_authenticate})
        login(ANONYMOUS)
        repository = getUtility(IGitRepositorySet).getByPath(
            requester, path.lstrip("/"))
        self.assertIsNotNone(repository)
        self.assertEqual(requester, repository.registrant)
        self.assertEqual(
            {"path": repository.getInternalPath(), "writable": True,
             "trailing": "", "private": private},
            translation)
        self.assertEqual(
            (repository.getInternalPath(),),
            self.hosting_fixture.create.extract_args()[0])
        self.assertEqual(GitRepositoryType.HOSTED, repository.repository_type)
        return repository

    def assertCreatesFromClone(self, requester, path, cloned_from,
                               can_authenticate=False):
        self.assertCreates(requester, path, can_authenticate)
        self.assertEqual(
            {"clone_from": cloned_from.getInternalPath()},
            self.hosting_fixture.create.extract_kwargs()[0])

    def test_translatePath_private_repository(self):
        requester = self.factory.makePerson()
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(
                owner=requester, information_type=InformationType.USERDATA))
        path = u"/%s" % repository.unique_name
        self.assertTranslates(requester, path, repository, True, private=True)

    def test_translatePath_cannot_see_private_repository(self):
        requester = self.factory.makePerson()
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(
                information_type=InformationType.USERDATA))
        path = u"/%s" % repository.unique_name
        self.assertGitRepositoryNotFound(requester, path)

    def test_translatePath_anonymous_cannot_see_private_repository(self):
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(
                information_type=InformationType.USERDATA))
        path = u"/%s" % repository.unique_name
        self.assertGitRepositoryNotFound(None, path, can_authenticate=False)
        self.assertUnauthorized(None, path, can_authenticate=True)

    def test_translatePath_team_unowned(self):
        requester = self.factory.makePerson()
        team = self.factory.makeTeam(self.factory.makePerson())
        repository = self.factory.makeGitRepository(owner=team)
        path = u"/%s" % repository.unique_name
        self.assertTranslates(requester, path, repository, False)
        self.assertPermissionDenied(requester, path, permission="write")

    def test_translatePath_imported(self):
        requester = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            owner=requester, repository_type=GitRepositoryType.IMPORTED)
        path = u"/%s" % repository.unique_name
        self.assertTranslates(requester, path, repository, False)
        self.assertPermissionDenied(requester, path, permission="write")

    def test_translatePath_create_personal_team_denied(self):
        # translatePath refuses to create a personal repository for a team
        # of which the requester is not a member.
        requester = self.factory.makePerson()
        team = self.factory.makeTeam()
        message = "%s is not a member of %s" % (
            requester.displayname, team.displayname)
        self.assertPermissionDenied(
            requester, u"/~%s/+git/random" % team.name, message=message,
            permission="write")

    def test_translatePath_create_other_user(self):
        # Creating a repository for another user fails.
        requester = self.factory.makePerson()
        other_person = self.factory.makePerson()
        project = self.factory.makeProduct()
        name = self.factory.getUniqueString()
        path = u"/~%s/%s/+git/%s" % (other_person.name, project.name, name)
        message = "%s cannot create Git repositories owned by %s" % (
            requester.displayname, other_person.displayname)
        self.assertPermissionDenied(
            requester, path, message=message, permission="write")

    def test_translatePath_create_project_not_owner(self):
        # Somebody without edit permission on the project cannot create a
        # repository and immediately set it as the default for that project.
        requester = self.factory.makePerson()
        project = self.factory.makeProduct()
        path = u"/%s" % project.name
        message = "%s cannot create Git repositories owned by %s" % (
            requester.displayname, project.owner.displayname)
        initial_count = getUtility(IAllGitRepositories).count()
        self.assertPermissionDenied(
            requester, path, message=message, permission="write")
        # No repository was created.
        login(ANONYMOUS)
        self.assertEqual(
            initial_count, getUtility(IAllGitRepositories).count())

    def test_listRefRules_simple(self):
        # Test that correct ref rules are retrieved for a Person
        requester = self.factory.makePerson()
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(
                owner=requester, information_type=InformationType.USERDATA))

        rule = self.factory.makeGitRule(repository)
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=requester, can_push=True, can_create=True)

        results = self.git_api.listRefRules(
            repository.getInternalPath(),
            {'uid': requester.id})
        self.assertThat(results, MatchesListwise([
            MatchesDict({
                'ref_pattern': Equals('refs/heads/*'),
                'permissions': Equals(['create', 'push']),
                }),
            MatchesDict({
                'ref_pattern': Equals('*'),
                'permissions': Equals(['create', 'push', 'force-push']),
                }),
            ]))

    def test_listRefRules_with_other_grants(self):
        # Test that findGrantsByGrantee only returns relevant rules
        requester = self.factory.makePerson()
        other_user = self.factory.makePerson()
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(
                owner=requester, information_type=InformationType.USERDATA))

        rule = self.factory.makeGitRule(repository)
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=requester, can_push=True)
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=other_user, can_create=True)

        results = self.git_api.listRefRules(
            repository.getInternalPath(),
            {'uid': requester.id})
        self.assertThat(results, MatchesListwise([
            MatchesDict({
                'ref_pattern': Equals('refs/heads/*'),
                'permissions': Equals(['push']),
                }),
            MatchesDict({
                'ref_pattern': Equals('*'),
                'permissions': Equals(['create', 'push', 'force-push']),
                }),
            ]))

    def test_listRefRules_no_grants(self):
        # User that has no grants and is not the owner
        requester = self.factory.makePerson()
        owner = self.factory.makePerson()
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(
                owner=owner, information_type=InformationType.USERDATA))

        rule = self.factory.makeGitRule(repository)
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=owner, can_push=True, can_create=True)

        results = self.git_api.listRefRules(
            repository.getInternalPath(),
            {'uid': requester.id})
        self.assertEqual(0, len(results))

    def test_listRefRules_owner_has_default(self):
        owner = self.factory.makePerson()
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(
                owner=owner, information_type=InformationType.USERDATA))

        rule = self.factory.makeGitRule(
            repository=repository, ref_pattern=u'refs/heads/master')
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=owner, can_push=True, can_create=True)

        results = self.git_api.listRefRules(
            repository.getInternalPath(),
            {'uid': owner.id})
        self.assertEqual(len(results), 2)
        # Default grant should be last in pattern
        self.assertThat(results, MatchesListwise([
            MatchesDict({
                'ref_pattern': Equals('refs/heads/master'),
                'permissions': Equals(['create', 'push']),
                }),
            MatchesDict({
                'ref_pattern': Equals('*'),
                'permissions': Equals(['create', 'push', 'force-push']),
                }),
            ]))

    def test_listRefRules_owner_is_team(self):
        member = self.factory.makePerson()
        owner = self.factory.makeTeam(members=[member])
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(
                owner=owner, information_type=InformationType.USERDATA))

        results = self.git_api.listRefRules(
            repository.getInternalPath(),
            {'uid': member.id})

        # Should have default grant as member of owning team
        self.assertThat(results, MatchesListwise([
            MatchesDict({
                'ref_pattern': Equals('*'),
                'permissions': Equals(['create', 'push', 'force-push']),
                }),
            ]))

    def test_listRefRules_owner_is_team_with_grants(self):
        member = self.factory.makePerson()
        owner = self.factory.makeTeam(members=[member])
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(
                owner=owner, information_type=InformationType.USERDATA))

        rule = self.factory.makeGitRule(
            repository=repository, ref_pattern=u'refs/heads/master')
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=owner, can_push=True, can_create=True)

        results = self.git_api.listRefRules(
            repository.getInternalPath(),
            {'uid': member.id})

        # Should have default grant as member of owning team
        self.assertThat(results, MatchesListwise([
            MatchesDict({
                'ref_pattern': Equals('refs/heads/master'),
                'permissions': Equals(['create', 'push']),
                }),
            MatchesDict({
                'ref_pattern': Equals('*'),
                'permissions': Equals(['create', 'push', 'force-push']),
                }),
            ]))

    def test_listRefRules_owner_is_team_with_grants_to_person(self):
        member = self.factory.makePerson()
        other_member = self.factory.makePerson()
        owner = self.factory.makeTeam(members=[member, other_member])
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(
                owner=owner, information_type=InformationType.USERDATA))

        rule = self.factory.makeGitRule(
            repository=repository, ref_pattern=u'refs/heads/master')
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=owner, can_push=True, can_create=True)

        rule = self.factory.makeGitRule(
            repository=repository, ref_pattern=u'refs/heads/tags')
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=member, can_create=True)

        # This should not appear
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=other_member, can_push=True)

        results = self.git_api.listRefRules(
            repository.getInternalPath(),
            {'uid': member.id})

        # Should have default grant as member of owning team
        self.assertThat(results, MatchesListwise([
            MatchesDict({
                'ref_pattern': Equals('refs/heads/tags'),
                'permissions': Equals(['create']),
                }),
            MatchesDict({
                'ref_pattern': Equals('refs/heads/master'),
                'permissions': Equals(['create', 'push']),
                }),
            MatchesDict({
                'ref_pattern': Equals('*'),
                'permissions': Equals(['create', 'push', 'force-push']),
                }),
            ]))

    def test_listRefRules_multiple_grants_to_same_ref(self):
        member = self.factory.makePerson()
        owner = self.factory.makeTeam(members=[member])
        repository = removeSecurityProxy(
            self.factory.makeGitRepository(
                owner=owner, information_type=InformationType.USERDATA))

        rule = self.factory.makeGitRule(repository=repository)
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=member, can_create=True)
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=owner, can_push=True)

        results = self.git_api.listRefRules(
            repository.getInternalPath(),
            {'uid': member.id})

        self.assertThat(results, MatchesListwise([
            MatchesDict({
                'ref_pattern': Equals('refs/heads/*'),
                'permissions': Equals(['create', 'push']),
                }),
            MatchesDict({
                'ref_pattern': Equals('*'),
                'permissions': Equals(['create', 'push', 'force-push']),
                }),
            ]))


class TestGitAPI(TestGitAPIMixin, TestCaseWithFactory):
    """Tests for the implementation of `IGitAPI`."""

    layer = LaunchpadFunctionalLayer

    def test_translatePath_cannot_translate(self):
        # Sometimes translatePath will not know how to translate a path.
        # When this happens, it returns a Fault saying so, including the
        # path it couldn't translate.
        requester = self.factory.makePerson()
        self.assertGitRepositoryNotFound(requester, u"/untranslatable")

    def test_translatePath_repository(self):
        requester = self.factory.makePerson()
        repository = self.factory.makeGitRepository()
        path = u"/%s" % repository.unique_name
        self.assertTranslates(requester, path, repository, False)

    def test_translatePath_repository_with_no_leading_slash(self):
        requester = self.factory.makePerson()
        repository = self.factory.makeGitRepository()
        path = repository.unique_name
        self.assertTranslates(requester, path, repository, False)

    def test_translatePath_repository_with_trailing_slash(self):
        requester = self.factory.makePerson()
        repository = self.factory.makeGitRepository()
        path = u"/%s/" % repository.unique_name
        self.assertTranslates(requester, path, repository, False)

    def test_translatePath_repository_with_trailing_segments(self):
        requester = self.factory.makePerson()
        repository = self.factory.makeGitRepository()
        path = u"/%s/foo/bar" % repository.unique_name
        self.assertTranslates(
            requester, path, repository, False, trailing="foo/bar")

    def test_translatePath_no_such_repository(self):
        requester = self.factory.makePerson()
        path = u"/%s/+git/no-such-repository" % requester.name
        self.assertGitRepositoryNotFound(requester, path)

    def test_translatePath_no_such_repository_non_ascii(self):
        requester = self.factory.makePerson()
        path = u"/%s/+git/\N{LATIN SMALL LETTER I WITH DIAERESIS}" % (
            requester.name)
        self.assertGitRepositoryNotFound(requester, path)

    def test_translatePath_anonymous_public_repository(self):
        repository = self.factory.makeGitRepository()
        path = u"/%s" % repository.unique_name
        self.assertTranslates(
            None, path, repository, False, can_authenticate=False)
        self.assertTranslates(
            None, path, repository, False, can_authenticate=True)

    def test_translatePath_owned(self):
        requester = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=requester)
        path = u"/%s" % repository.unique_name
        self.assertTranslates(
            requester, path, repository, True, permission="write")

    def test_translatePath_team_owned(self):
        requester = self.factory.makePerson()
        team = self.factory.makeTeam(requester)
        repository = self.factory.makeGitRepository(owner=team)
        path = u"/%s" % repository.unique_name
        self.assertTranslates(
            requester, path, repository, True, permission="write")

    def test_translatePath_shortened_path(self):
        # translatePath translates the shortened path to a repository.
        requester = self.factory.makePerson()
        repository = self.factory.makeGitRepository()
        with person_logged_in(repository.target.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                repository.target, repository)
        path = u"/%s" % repository.target.name
        self.assertTranslates(requester, path, repository, False)

    def test_translatePath_create_project(self):
        # translatePath creates a project repository that doesn't exist, if
        # it can.
        requester = self.factory.makePerson()
        project = self.factory.makeProduct()
        self.assertCreates(
            requester, u"/~%s/%s/+git/random" % (requester.name, project.name))

    def test_translatePath_create_project_clone_from_target_default(self):
        # translatePath creates a project repository cloned from the target
        # default if it exists.
        target = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(
            owner=target.owner, target=target)
        with person_logged_in(target.owner):
            self.repository_set.setDefaultRepository(target, repository)
            self.assertCreatesFromClone(
                target.owner,
                u"/~%s/%s/+git/random" % (target.owner.name, target.name),
                repository)

    def test_translatePath_create_project_clone_from_owner_default(self):
        # translatePath creates a project repository cloned from the owner
        # default if it exists and the target default does not.
        target = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(
            owner=target.owner, target=target)
        with person_logged_in(target.owner) as user:
            self.repository_set.setDefaultRepositoryForOwner(
                target.owner, target, repository, user)
            self.assertCreatesFromClone(
                target.owner,
                u"/~%s/%s/+git/random" % (target.owner.name, target.name),
                repository)

    def test_translatePath_create_package(self):
        # translatePath creates a package repository that doesn't exist, if
        # it can.
        requester = self.factory.makePerson()
        dsp = self.factory.makeDistributionSourcePackage()
        self.assertCreates(
            requester,
            u"/~%s/%s/+source/%s/+git/random" % (
                requester.name,
                dsp.distribution.name, dsp.sourcepackagename.name))

    def test_translatePath_create_personal(self):
        # translatePath creates a personal repository that doesn't exist, if
        # it can.
        requester = self.factory.makePerson()
        self.assertCreates(requester, u"/~%s/+git/random" % requester.name)

    def test_translatePath_create_personal_team(self):
        # translatePath creates a personal repository for a team of which
        # the requester is a member.
        requester = self.factory.makePerson()
        team = self.factory.makeTeam(members=[requester])
        self.assertCreates(requester, u"/~%s/+git/random" % team.name)

    def test_translatePath_create_bytestring(self):
        # ASCII strings come in as bytestrings, not Unicode strings. They
        # work fine too.
        requester = self.factory.makePerson()
        project = self.factory.makeProduct()
        path = u"/~%s/%s/+git/random" % (requester.name, project.name)
        self.assertCreates(requester, path.encode('ascii'))

    def test_translatePath_anonymous_cannot_create(self):
        # Anonymous users cannot create repositories.
        project = self.factory.makeProject()
        self.assertGitRepositoryNotFound(
            None, u"/%s" % project.name, permission="write",
            can_authenticate=False)
        self.assertUnauthorized(
            None, u"/%s" % project.name, permission="write",
            can_authenticate=True)

    def test_translatePath_create_invalid_namespace(self):
        # Trying to create a repository at a path that isn't valid for Git
        # repositories returns a PermissionDenied fault.
        requester = self.factory.makePerson()
        path = u"/~%s" % requester.name
        message = "'%s' is not a valid Git repository path." % path.strip("/")
        self.assertPermissionDenied(
            requester, path, message=message, permission="write")

    def test_translatePath_create_no_such_person(self):
        # Creating a repository for a non-existent person fails.
        requester = self.factory.makePerson()
        self.assertNotFound(
            requester, u"/~nonexistent/+git/random",
            "User/team 'nonexistent' does not exist.", permission="write")

    def test_translatePath_create_no_such_project(self):
        # Creating a repository for a non-existent project fails.
        requester = self.factory.makePerson()
        self.assertNotFound(
            requester, u"/~%s/nonexistent/+git/random" % requester.name,
            "Project 'nonexistent' does not exist.", permission="write")

    def test_translatePath_create_no_such_person_or_project(self):
        # If neither the person nor the project are found, then the missing
        # person is reported in preference.
        requester = self.factory.makePerson()
        self.assertNotFound(
            requester, u"/~nonexistent/nonexistent/+git/random",
            "User/team 'nonexistent' does not exist.", permission="write")

    def test_translatePath_create_invalid_project(self):
        # Creating a repository with an invalid project name fails.
        requester = self.factory.makePerson()
        self.assertNotFound(
            requester, u"/_bad_project/+git/random",
            "Project '_bad_project' does not exist.", permission="write")

    def test_translatePath_create_missing_sourcepackagename(self):
        # If translatePath is asked to create a repository for a missing
        # source package, it will create the source package.
        requester = self.factory.makePerson()
        distro = self.factory.makeDistribution()
        repository_name = self.factory.getUniqueString()
        path = u"/~%s/%s/+source/new-package/+git/%s" % (
            requester.name, distro.name, repository_name)
        repository = self.assertCreates(requester, path)
        self.assertEqual(
            "new-package", repository.target.sourcepackagename.name)

    def test_translatePath_create_invalid_sourcepackagename(self):
        # Creating a repository for an invalid source package name fails.
        requester = self.factory.makePerson()
        distro = self.factory.makeDistribution()
        repository_name = self.factory.getUniqueString()
        path = u"/~%s/%s/+source/new package/+git/%s" % (
            requester.name, distro.name, repository_name)
        self.assertInvalidSourcePackageName(
            requester, path, "new package", permission="write")

    def test_translatePath_create_bad_name(self):
        # Creating a repository with an invalid name fails.
        requester = self.factory.makePerson()
        project = self.factory.makeProduct()
        invalid_name = "invalid name!"
        path = u"/~%s/%s/+git/%s" % (
            requester.name, project.name, invalid_name)
        # LaunchpadValidationError unfortunately assumes its output is
        # always HTML, so it ends up double-escaped in XML-RPC faults.
        message = html_escape(
            "Invalid Git repository name '%s'. %s" %
            (invalid_name, GIT_REPOSITORY_NAME_VALIDATION_ERROR_MESSAGE))
        self.assertInvalidBranchName(
            requester, path, message, permission="write")

    def test_translatePath_create_unicode_name(self):
        # Creating a repository with a non-ASCII invalid name fails.
        requester = self.factory.makePerson()
        project = self.factory.makeProduct()
        invalid_name = u"invalid\N{LATIN SMALL LETTER E WITH ACUTE}"
        path = u"/~%s/%s/+git/%s" % (
            requester.name, project.name, invalid_name)
        # LaunchpadValidationError unfortunately assumes its output is
        # always HTML, so it ends up double-escaped in XML-RPC faults.
        message = html_escape(
            "Invalid Git repository name '%s'. %s" %
            (invalid_name, GIT_REPOSITORY_NAME_VALIDATION_ERROR_MESSAGE))
        self.assertInvalidBranchName(
            requester, path, message, permission="write")

    def test_translatePath_create_project_default(self):
        # A repository can be created and immediately set as the default for
        # a project.
        requester = self.factory.makePerson()
        owner = self.factory.makeTeam(
            membership_policy=TeamMembershipPolicy.RESTRICTED,
            members=[requester])
        project = self.factory.makeProduct(owner=owner)
        repository = self.assertCreates(requester, u"/%s" % project.name)
        self.assertTrue(repository.target_default)
        self.assertTrue(repository.owner_default)
        self.assertEqual(owner, repository.owner)

    def test_translatePath_create_package_default_denied(self):
        # A repository cannot (yet) be created and immediately set as the
        # default for a package.
        requester = self.factory.makePerson()
        dsp = self.factory.makeDistributionSourcePackage()
        path = u"/%s/+source/%s" % (
            dsp.distribution.name, dsp.sourcepackagename.name)
        message = (
            "Cannot automatically set the default repository for this target; "
            "push to a named repository instead.")
        self.assertPermissionDenied(
            requester, path, message=message, permission="write")

    def test_translatePath_create_project_owner_default(self):
        # A repository can be created and immediately set as its owner's
        # default for a project.
        requester = self.factory.makePerson()
        project = self.factory.makeProduct()
        repository = self.assertCreates(
            requester, u"/~%s/%s" % (requester.name, project.name))
        self.assertFalse(repository.target_default)
        self.assertTrue(repository.owner_default)
        self.assertEqual(requester, repository.owner)

    def test_translatePath_create_project_team_owner_default(self):
        # The owner of a team can create a team-owned repository and
        # immediately set it as that team's default for a project.
        requester = self.factory.makePerson()
        team = self.factory.makeTeam(owner=requester)
        project = self.factory.makeProduct()
        repository = self.assertCreates(
            requester, u"/~%s/%s" % (team.name, project.name))
        self.assertFalse(repository.target_default)
        self.assertTrue(repository.owner_default)
        self.assertEqual(team, repository.owner)

    def test_translatePath_create_project_team_member_default(self):
        # A non-owner member of a team can create a team-owned repository
        # and immediately set it as that team's default for a project.
        requester = self.factory.makePerson()
        team = self.factory.makeTeam(members=[requester])
        project = self.factory.makeProduct()
        repository = self.assertCreates(
            requester, u"/~%s/%s" % (team.name, project.name))
        self.assertFalse(repository.target_default)
        self.assertTrue(repository.owner_default)
        self.assertEqual(team, repository.owner)

    def test_translatePath_create_package_owner_default(self):
        # A repository can be created and immediately set as its owner's
        # default for a package.
        requester = self.factory.makePerson()
        dsp = self.factory.makeDistributionSourcePackage()
        path = u"/~%s/%s/+source/%s" % (
            requester.name, dsp.distribution.name, dsp.sourcepackagename.name)
        repository = self.assertCreates(requester, path)
        self.assertFalse(repository.target_default)
        self.assertTrue(repository.owner_default)
        self.assertEqual(requester, repository.owner)

    def test_translatePath_create_package_team_owner_default(self):
        # The owner of a team can create a team-owned repository and
        # immediately set it as that team's default for a package.
        requester = self.factory.makePerson()
        team = self.factory.makeTeam(owner=requester)
        dsp = self.factory.makeDistributionSourcePackage()
        path = u"/~%s/%s/+source/%s" % (
            team.name, dsp.distribution.name, dsp.sourcepackagename.name)
        repository = self.assertCreates(requester, path)
        self.assertFalse(repository.target_default)
        self.assertTrue(repository.owner_default)
        self.assertEqual(team, repository.owner)

    def test_translatePath_create_package_team_member_default(self):
        # A non-owner member of a team can create a team-owned repository
        # and immediately set it as that team's default for a package.
        requester = self.factory.makePerson()
        team = self.factory.makeTeam(members=[requester])
        dsp = self.factory.makeDistributionSourcePackage()
        path = u"/~%s/%s/+source/%s" % (
            team.name, dsp.distribution.name, dsp.sourcepackagename.name)
        repository = self.assertCreates(requester, path)
        self.assertFalse(repository.target_default)
        self.assertTrue(repository.owner_default)
        self.assertEqual(team, repository.owner)

    def test_translatePath_create_broken_hosting_service(self):
        # If the hosting service is down, trying to create a repository
        # fails and doesn't leave junk around in the Launchpad database.
        self.hosting_fixture.create.failure = GitRepositoryCreationFault(
            "nothing here")
        requester = self.factory.makePerson()
        initial_count = getUtility(IAllGitRepositories).count()
        oops_id = self.assertOopsOccurred(
            requester, u"/~%s/+git/random" % requester.name,
            permission="write")
        login(ANONYMOUS)
        self.assertEqual(
            initial_count, getUtility(IAllGitRepositories).count())
        # The error report OOPS ID should match the fault, and the traceback
        # text should show the underlying exception.
        self.assertEqual(1, len(self.oopses))
        self.assertEqual(oops_id, self.oopses[0]["id"])
        self.assertIn(
            "GitRepositoryCreationFault: nothing here",
            self.oopses[0]["tb_text"])

    def test_translatePath_code_import(self):
        # A code import worker with a suitable macaroon can write to a
        # repository associated with a running code import job.
        self.pushConfig("codeimport", macaroon_secret_key="some-secret")
        machine = self.factory.makeCodeImportMachine(set_online=True)
        code_imports = [
            self.factory.makeCodeImport(
                target_rcs_type=TargetRevisionControlSystems.GIT)
            for _ in range(2)]
        with celebrity_logged_in("vcs_imports"):
            jobs = [
                self.factory.makeCodeImportJob(code_import=code_import)
                for code_import in code_imports]
        issuer = getUtility(IMacaroonIssuer, "code-import-job")
        macaroons = [
            removeSecurityProxy(issuer).issueMacaroon(job) for job in jobs]
        path = u"/%s" % code_imports[0].git_repository.unique_name
        self.assertPermissionDenied(
            None, path, permission="write", macaroon_raw=macaroons[0])
        with celebrity_logged_in("vcs_imports"):
            getUtility(ICodeImportJobWorkflow).startJob(jobs[0], machine)
        self.assertTranslates(
            None, path, code_imports[0].git_repository, True,
            permission="write", macaroon_raw=macaroons[0].serialize())
        self.assertPermissionDenied(
            None, path, permission="write",
            macaroon_raw=macaroons[1].serialize())
        self.assertPermissionDenied(
            None, path, permission="write",
            macaroon_raw=Macaroon(
                location=config.vhost.mainsite.hostname, identifier="another",
                key="another-secret").serialize())
        self.assertPermissionDenied(
            None, path, permission="write", macaroon_raw="nonsense")

    def test_translatePath_private_code_import(self):
        # A code import worker with a suitable macaroon can write to a
        # repository associated with a running private code import job.
        self.pushConfig("codeimport", macaroon_secret_key="some-secret")
        machine = self.factory.makeCodeImportMachine(set_online=True)
        code_imports = [
            self.factory.makeCodeImport(
                target_rcs_type=TargetRevisionControlSystems.GIT)
            for _ in range(2)]
        private_repository = code_imports[0].git_repository
        removeSecurityProxy(private_repository).transitionToInformationType(
            InformationType.PRIVATESECURITY, private_repository.owner)
        with celebrity_logged_in("vcs_imports"):
            jobs = [
                self.factory.makeCodeImportJob(code_import=code_import)
                for code_import in code_imports]
        issuer = getUtility(IMacaroonIssuer, "code-import-job")
        macaroons = [
            removeSecurityProxy(issuer).issueMacaroon(job) for job in jobs]
        path = u"/%s" % code_imports[0].git_repository.unique_name
        self.assertPermissionDenied(
            None, path, permission="write", macaroon_raw=macaroons[0])
        with celebrity_logged_in("vcs_imports"):
            getUtility(ICodeImportJobWorkflow).startJob(jobs[0], machine)
        self.assertTranslates(
            None, path, code_imports[0].git_repository, True,
            permission="write", macaroon_raw=macaroons[0].serialize(),
            private=True)
        # The expected faults are slightly different from the public case,
        # because we deny the existence of private repositories.
        self.assertGitRepositoryNotFound(
            None, path, permission="write",
            macaroon_raw=macaroons[1].serialize())
        self.assertGitRepositoryNotFound(
            None, path, permission="write",
            macaroon_raw=Macaroon(
                location=config.vhost.mainsite.hostname, identifier="another",
                key="another-secret").serialize())
        self.assertGitRepositoryNotFound(
            None, path, permission="write", macaroon_raw="nonsense")

    def test_notify(self):
        # The notify call creates a GitRefScanJob.
        repository = self.factory.makeGitRepository()
        self.assertIsNone(self.git_api.notify(repository.getInternalPath()))
        job_source = getUtility(IGitRefScanJobSource)
        [job] = list(job_source.iterReady())
        self.assertEqual(repository, job.repository)

    def test_notify_missing_repository(self):
        # A notify call on a non-existent repository returns a fault and
        # does not create a job.
        fault = self.git_api.notify("10000")
        self.assertIsInstance(fault, faults.NotFound)
        job_source = getUtility(IGitRefScanJobSource)
        self.assertEqual([], list(job_source.iterReady()))

    def test_notify_private(self):
        # notify works on private repos.
        with admin_logged_in():
            repository = self.factory.makeGitRepository(
                information_type=InformationType.PRIVATESECURITY)
            path = repository.getInternalPath()
        self.assertIsNone(self.git_api.notify(path))
        job_source = getUtility(IGitRefScanJobSource)
        [job] = list(job_source.iterReady())
        self.assertEqual(repository, job.repository)

    def test_authenticateWithPassword(self):
        self.assertIsInstance(
            self.git_api.authenticateWithPassword('foo', 'bar'),
            faults.Unauthorized)

    def test_authenticateWithPassword_code_import(self):
        self.pushConfig("codeimport", macaroon_secret_key="some-secret")
        code_import = self.factory.makeCodeImport(
            target_rcs_type=TargetRevisionControlSystems.GIT)
        with celebrity_logged_in("vcs_imports"):
            job = self.factory.makeCodeImportJob(code_import=code_import)
        issuer = getUtility(IMacaroonIssuer, "code-import-job")
        macaroon = removeSecurityProxy(issuer).issueMacaroon(job)
        self.assertEqual(
            {"macaroon": macaroon.serialize()},
            self.git_api.authenticateWithPassword("", macaroon.serialize()))
        other_macaroon = Macaroon(identifier="another", key="another-secret")
        self.assertIsInstance(
            self.git_api.authenticateWithPassword(
                "", other_macaroon.serialize()),
            faults.Unauthorized)
        self.assertIsInstance(
            self.git_api.authenticateWithPassword("", "nonsense"),
            faults.Unauthorized)


class TestGitAPISecurity(TestGitAPIMixin, TestCaseWithFactory):
    """Slow tests for `IGitAPI`.

    These use AppServerLayer to check that `run_with_login` is behaving
    itself properly.
    """

    layer = AppServerLayer
