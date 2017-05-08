# Copyright 2010-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the source package recipe view classes and templates."""

__metaclass__ = type


from datetime import (
    datetime,
    timedelta,
    )
import re
from textwrap import dedent

from BeautifulSoup import BeautifulSoup
from fixtures import FakeLogger
from mechanize import LinkNotFoundError
from pytz import UTC
from testtools.matchers import Equals
import transaction
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import InformationType
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.processor import IProcessorSet
from lp.code.browser.sourcepackagerecipe import (
    SourcePackageRecipeEditView,
    SourcePackageRecipeRequestBuildsView,
    SourcePackageRecipeRequestDailyBuildView,
    SourcePackageRecipeView,
    )
from lp.code.browser.sourcepackagerecipebuild import (
    SourcePackageRecipeBuildView,
    )
from lp.code.interfaces.sourcepackagerecipe import (
    MINIMAL_RECIPE_TEXT_BZR,
    MINIMAL_RECIPE_TEXT_GIT,
    )
from lp.code.tests.helpers import (
    GitHostingFixture,
    recipe_parser_newest_version,
    )
from lp.registry.interfaces.person import TeamMembershipPolicy
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.interfaces.teammembership import TeamMembershipStatus
from lp.services.database.constants import UTC_NOW
from lp.services.propertycache import clear_property_cache
from lp.services.webapp import canonical_url
from lp.services.webapp.escaping import html_escape
from lp.services.webapp.interfaces import ILaunchpadRoot
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import (
    admin_logged_in,
    ANONYMOUS,
    BrowserTestCase,
    login,
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    time_counter,
    )
from lp.testing.deprecated import LaunchpadFormHarness
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.matchers import (
    MatchesPickerText,
    MatchesTagText,
    )
from lp.testing.pages import (
    extract_text,
    find_main_content,
    find_tag_by_id,
    find_tags_by_class,
    get_feedback_messages,
    get_radio_button_text_for_field,
    )
from lp.testing.views import create_initialized_view


class TestCanonicalUrlForRecipe(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_canonical_url(self):
        owner = self.factory.makePerson(name='recipe-owner')
        recipe = self.factory.makeSourcePackageRecipe(
            owner=owner, name=u'recipe-name')
        self.assertEqual(
            'http://code.launchpad.dev/~recipe-owner/+recipe/recipe-name',
            canonical_url(recipe))


class BzrMixin:
    """Mixin for Bazaar-based recipe tests."""

    minimal_recipe_text = MINIMAL_RECIPE_TEXT_BZR
    branch_type = "branch"
    no_such_object_message = "is not a branch on Launchpad."

    def makeBranch(self, target=None, **kwargs):
        return self.factory.makeAnyBranch(product=target, **kwargs)

    def makePackageBranch(self, **kwargs):
        return self.factory.makePackageBranch(**kwargs)

    def makeRelatedBranches(self, *args, **kwargs):
        return self.factory.makeRelatedBranches(*args, **kwargs)

    def checkRelatedBranches(self, related_series_branch_info,
                             related_package_branch_info, browser_contents):
        """Check that the browser contents contain the correct branch info."""
        login(ANONYMOUS)
        soup = BeautifulSoup(browser_contents)

        # The related branches collapsible section needs to be there.
        related_branches = soup.find('fieldset', {'id': 'related-branches'})
        self.assertIsNot(related_branches, None)

        # Check the related package branches.
        root_url = canonical_url(
            getUtility(ILaunchpadRoot), rootsite='code')
        root_url = root_url.rstrip('/')
        branch_table = soup.find(
            'table', {'id': 'related-package-branches-listing'})
        if not related_package_branch_info:
            self.assertIs(branch_table, None)
        else:
            rows = branch_table.tbody.findAll('tr')

            package_branches_info = []
            for row in rows:
                branch_links = row.findAll('a')
                self.assertEqual(2, len(branch_links))
                package_branches_info.append(
                    '%s%s' % (root_url, branch_links[0]['href']))
                package_branches_info.append(branch_links[0].renderContents())
                package_branches_info.append(
                    '%s%s' % (root_url, branch_links[1]['href']))
                package_branches_info.append(branch_links[1].renderContents())
            expected_branch_info = []
            for branch_info in related_package_branch_info:
                branch = branch_info[0]
                distro_series = branch_info[1]
                expected_branch_info.append(
                    canonical_url(branch, rootsite='code'))
                expected_branch_info.append(branch.displayname)
                expected_branch_info.append(
                    canonical_url(distro_series, rootsite='code'))
                expected_branch_info.append(distro_series.name)
            self.assertEqual(package_branches_info, expected_branch_info)

        # Check the related series branches.
        branch_table = soup.find(
            'table', {'id': 'related-series-branches-listing'})
        if not related_series_branch_info:
            self.assertIs(branch_table, None)
        else:
            rows = branch_table.tbody.findAll('tr')

            series_branches_info = []
            for row in rows:
                branch_links = row.findAll('a')
                self.assertEqual(2, len(branch_links))
                series_branches_info.append(
                    '%s%s' % (root_url, branch_links[0]['href']))
                series_branches_info.append(branch_links[0].renderContents())
                series_branches_info.append(branch_links[1]['href'])
                series_branches_info.append(branch_links[1].renderContents())
            expected_branch_info = []
            for branch_info in related_series_branch_info:
                branch = branch_info[0]
                product_series = branch_info[1]
                expected_branch_info.append(
                    canonical_url(branch,
                                  rootsite='code',
                                  path_only_if_possible=True))
                expected_branch_info.append(branch.displayname)
                expected_branch_info.append(
                    canonical_url(product_series,
                                  path_only_if_possible=True))
                expected_branch_info.append(product_series.name)
            self.assertEqual(expected_branch_info, series_branches_info)

    @staticmethod
    def getRepository(branch):
        return branch

    @staticmethod
    def getBranchRecipeText(branch):
        return branch.identity

    @staticmethod
    def getMinimalRecipeText(branch):
        return MINIMAL_RECIPE_TEXT_BZR % branch.identity


class GitMixin:
    """Mixin for Git-based recipe tests."""

    minimal_recipe_text = MINIMAL_RECIPE_TEXT_GIT
    branch_type = "repository"
    no_such_object_message = "is not a Git repository on Launchpad."

    def makeBranch(self, **kwargs):
        return self.factory.makeGitRefs(**kwargs)[0]

    def makePackageBranch(self, sourcepackagename=None, **kwargs):
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename=sourcepackagename)
        return self.factory.makeGitRefs(target=dsp, **kwargs)[0]

    def makeRelatedBranches(self, reference_branch=None, *args, **kwargs):
        if reference_branch is None:
            [reference_branch] = self.factory.makeGitRefs()
        return reference_branch, [], []

    def checkRelatedBranches(self, *args, **kwargs):
        pass

    @staticmethod
    def getRepository(branch):
        return branch.repository

    @staticmethod
    def getBranchRecipeText(branch):
        return "%s %s" % (branch.repository.identity, branch.name)

    @staticmethod
    def getMinimalRecipeText(branch):
        return MINIMAL_RECIPE_TEXT_GIT % (
            branch.repository.identity, branch.name)


class TestCaseForRecipe(BrowserTestCase):
    """Create some sample data for recipe tests."""

    def setUp(self):
        """Provide useful defaults."""
        super(TestCaseForRecipe, self).setUp()
        self.chef = self.factory.makePerson(
            displayname='Master Chef', name='chef')
        self.user = self.chef
        self.ppa = self.factory.makeArchive(
            displayname='Secret PPA', owner=self.chef, name='ppa')
        self.squirrel = self.factory.makeDistroSeries(
            displayname='Secret Squirrel', name='secret', version='100.04',
            distribution=self.ppa.distribution)
        naked_squirrel = removeSecurityProxy(self.squirrel)
        naked_squirrel.nominatedarchindep = self.squirrel.newArch(
            'i386', getUtility(IProcessorSet).getByName('386'), False,
            self.chef)

    def makeRecipe(self, **kwargs):
        """Create and return a specific recipe."""
        chocolate = self.factory.makeProduct(name='chocolate')
        cake_branch = self.makeBranch(
            owner=self.chef, name=u'cake', target=chocolate)
        return self.factory.makeSourcePackageRecipe(
            owner=self.chef, distroseries=self.squirrel, name=u'cake_recipe',
            description=u'This recipe builds a foo for distro bar, with my'
            ' Secret Squirrel changes.', branches=[cake_branch],
            daily_build_archive=self.ppa, **kwargs)


class TestSourcePackageRecipeAddViewInitialValuesMixin:

    layer = DatabaseFunctionalLayer

    def test_initial_name_exists(self):
        # If the initial name exists, a generator is used to find an unused
        # name by appending a numbered suffix on the end.
        owner = self.factory.makePerson()
        self.factory.makeSourcePackageRecipe(
            owner=owner, name=u'widget-daily')
        widget = self.factory.makeProduct(name='widget')
        branch = self.makeBranch(target=widget)
        with person_logged_in(owner):
            view = create_initialized_view(branch, '+new-recipe')
        self.assertThat('widget-daily-1', Equals(view.initial_values['name']))

    def test_initial_series(self):
        # The initial series are those that are current or in development.
        archive = self.factory.makeArchive()
        experimental = self.factory.makeDistroSeries(
            distribution=archive.distribution,
            status=SeriesStatus.EXPERIMENTAL)
        development = self.factory.makeDistroSeries(
            distribution=archive.distribution,
            status=SeriesStatus.DEVELOPMENT)
        frozen = self.factory.makeDistroSeries(
            distribution=archive.distribution,
            status=SeriesStatus.FROZEN)
        current = self.factory.makeDistroSeries(
            distribution=archive.distribution,
            status=SeriesStatus.CURRENT)
        supported = self.factory.makeDistroSeries(
            distribution=archive.distribution,
            status=SeriesStatus.SUPPORTED)
        obsolete = self.factory.makeDistroSeries(
            distribution=archive.distribution,
            status=SeriesStatus.OBSOLETE)
        future = self.factory.makeDistroSeries(
            distribution=archive.distribution,
            status=SeriesStatus.FUTURE)
        branch = self.makeBranch()
        with person_logged_in(archive.owner):
            view = create_initialized_view(branch, '+new-recipe')
        series = set(view.initial_values['distroseries'])
        initial_series = set([development, current])
        self.assertEqual(initial_series, series.intersection(initial_series))
        other_series = set(
            [experimental, frozen, supported, obsolete, future])
        self.assertEqual(set(), series.intersection(other_series))


class TestSourcePackageRecipeAddViewInitialValuesBzr(
    TestSourcePackageRecipeAddViewInitialValuesMixin, BzrMixin,
    TestCaseWithFactory):

    def test_project_branch_initial_name(self):
        # When a project branch is used, the initial name is the name of the
        # project followed by "-daily".
        widget = self.factory.makeProduct(name='widget')
        branch = self.factory.makeProductBranch(widget)
        with person_logged_in(branch.owner):
            view = create_initialized_view(branch, '+new-recipe')
        self.assertThat('widget-daily', Equals(view.initial_values['name']))

    def test_package_branch_initial_name(self):
        # When a package branch is used, the initial name is the name of the
        # source package followed by "-daily".
        branch = self.factory.makePackageBranch(sourcepackagename='widget')
        with person_logged_in(branch.owner):
            view = create_initialized_view(branch, '+new-recipe')
        self.assertThat('widget-daily', Equals(view.initial_values['name']))

    def test_personal_branch_initial_name(self):
        # When a personal branch is used, the initial name is the name of
        # the branch followed by "-daily".  +junk-daily is neither valid nor
        # helpful.
        branch = self.factory.makePersonalBranch(name='widget')
        with person_logged_in(branch.owner):
            view = create_initialized_view(branch, '+new-recipe')
        self.assertThat('widget-daily', Equals(view.initial_values['name']))


class TestSourcePackageRecipeAddViewInitialValuesGit(
    TestSourcePackageRecipeAddViewInitialValuesMixin, GitMixin,
    TestCaseWithFactory):

    def test_project_repository_initial_name(self):
        # When a project repository is used, the initial name is the name of
        # the project followed by "-daily".
        widget = self.factory.makeProduct(name='widget')
        repository = self.factory.makeGitRepository(target=widget)
        with person_logged_in(repository.owner):
            view = create_initialized_view(repository, '+new-recipe')
        self.assertThat('widget-daily', Equals(view.initial_values['name']))

    def test_package_repository_initial_name(self):
        # When a package repository is used, the initial name is the name of
        # the source package followed by "-daily".
        dsp = self.factory.makeDistributionSourcePackage(
            sourcepackagename='widget')
        repository = self.factory.makeGitRepository(target=dsp)
        with person_logged_in(repository.owner):
            view = create_initialized_view(repository, '+new-recipe')
        self.assertThat('widget-daily', Equals(view.initial_values['name']))

    def test_personal_repository_initial_name(self):
        # When a personal repository is used, the initial name is the name
        # of the repository followed by "-daily".  <person-name>-daily is
        # not helpful.
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            owner=owner, target=owner, name=u'widget')
        with person_logged_in(repository.owner):
            view = create_initialized_view(repository, '+new-recipe')
        self.assertThat('widget-daily', Equals(view.initial_values['name']))


class TestSourcePackageRecipeAddViewMixin:

    layer = DatabaseFunctionalLayer

    def test_create_new_recipe_not_logged_in(self):
        self.useFixture(FakeLogger())
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        branch = self.makeBranch(
            owner=self.chef, target=product, name=u'veggies')

        browser = self.getViewBrowser(branch, no_login=True)
        self.assertRaises(
            Unauthorized, browser.getLink('Create packaging recipe').click)

    def test_create_new_recipe(self):
        branch = self.makeBranchAndPackage()
        # A new recipe can be created from the branch page.
        browser = self.getUserBrowser(canonical_url(branch), user=self.chef)
        browser.getLink('Create packaging recipe').click()

        browser.getControl(name='field.name').value = 'daily'
        browser.getControl('Description').value = 'Make some food!'
        browser.getControl('Create Recipe').click()

        content = find_main_content(browser.contents)
        self.assertEqual('daily\nEdit', extract_text(content.h1))
        self.assertThat(
            'Edit Make some food!',
            MatchesTagText(content, 'edit-description'))
        self.assertThat(
            'Master Chef', MatchesPickerText(content, 'edit-owner'))
        self.assertThat(
            'Secret PPA',
            MatchesPickerText(content, 'edit-daily_build_archive'))

    def test_create_new_recipe_private_branch(self):
        # Recipes can't be created on private branches.
        with person_logged_in(self.chef):
            branch = self.makeBranch(
                owner=self.chef, information_type=InformationType.USERDATA)
            branch_url = canonical_url(branch)

        browser = self.getUserBrowser(branch_url, user=self.chef)
        self.assertRaises(
            LinkNotFoundError,
            browser.getLink,
            'Create packaging recipe')

    def test_create_new_recipe_users_teams_as_owner_options(self):
        # Teams that the user is in are options for the recipe owner.
        self.factory.makeTeam(
            name='good-chefs', displayname='Good Chefs', members=[self.chef])
        browser = self.getViewBrowser(
            self.makeBranchAndPackage(), '+new-recipe', user=self.chef)
        # The options for the owner include the Good Chefs team.
        options = browser.getControl(name='field.owner.owner').displayOptions
        self.assertEquals(
            ['Good Chefs (good-chefs)', 'Master Chef (chef)'],
            sorted([str(option) for option in options]))

    def test_create_new_recipe_team_owner(self):
        # New recipes can be owned by teams that the user is a member of.
        team = self.factory.makeTeam(
            name='good-chefs', displayname='Good Chefs', members=[self.chef])
        browser = self.getViewBrowser(
            self.makeBranchAndPackage(), '+new-recipe', user=self.chef)
        browser.getControl(name='field.name').value = 'daily'
        browser.getControl('Description').value = 'Make some food!'
        browser.getControl('Other').click()
        browser.getControl(name='field.owner.owner').displayValue = [
            'Good Chefs']
        browser.getControl('Create Recipe').click()

        login(ANONYMOUS)
        recipe = team.getRecipe(u'daily')
        self.assertEqual(team, recipe.owner)
        self.assertEqual('daily', recipe.name)

    def test_create_new_recipe_suggests_user(self):
        """The current user is suggested as a recipe owner, once."""
        branch = self.makeBranch(owner=self.chef)
        text = self.getMainText(branch, '+new-recipe')
        self.assertTextMatchesExpressionIgnoreWhitespace(
            r'Owner: Master Chef \(chef\) Other:', text)

    def test_create_new_recipe_suggests_user_team(self):
        """If current user is a member of branch owner, it is suggested."""
        team = self.factory.makeTeam(
            name='branch-team', displayname='Branch Team',
            members=[self.chef])
        branch = self.makeBranch(owner=team)
        text = self.getMainText(branch, '+new-recipe')
        self.assertTextMatchesExpressionIgnoreWhitespace(
            r'Owner: Master Chef \(chef\)'
            r' Branch Team \(branch-team\) Other:', text)

    def test_create_new_recipe_ignores_non_user_team(self):
        """If current user isn't a member of branch owner, it is ignored."""
        team = self.factory.makeTeam(
            name='branch-team', displayname='Branch Team')
        branch = self.makeBranch(owner=team)
        text = self.getMainText(branch, '+new-recipe')
        self.assertTextMatchesExpressionIgnoreWhitespace(
            r'Owner: Master Chef \(chef\) Other:', text)

    def test_create_recipe_forbidden_instruction(self):
        # We don't allow the "run" instruction in our recipes.  Make sure this
        # is communicated to the user properly.
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        branch = self.makeBranch(
            owner=self.chef, target=product, name=u'veggies')
        browser = self.getViewBrowser(branch, '+new-recipe', user=self.chef)
        browser.getControl('Description').value = 'Make some food!'
        browser.getControl('Recipe text').value = (
            browser.getControl('Recipe text').value + 'run cat /etc/passwd')
        browser.getControl('Create Recipe').click()
        self.assertEqual(
            get_feedback_messages(browser.contents)[1],
            html_escape('The recipe instruction "run" is not permitted here.'))

    def createRecipe(self, recipe_text, branch=None):
        if branch is None:
            product = self.factory.makeProduct(
                name='ratatouille', displayname='Ratatouille')
            branch = self.makeBranch(
                owner=self.chef, target=product, name=u'veggies')
        browser = self.getViewBrowser(branch, '+new-recipe', user=self.chef)
        browser.getControl(name='field.name').value = 'daily'
        browser.getControl('Description').value = 'Make some food!'
        browser.getControl('Recipe text').value = recipe_text
        browser.getControl('Create Recipe').click()
        return browser

    def test_create_recipe_usage(self):
        # The error for a recipe with invalid instruction parameters should
        # include instruction usage.
        branch = self.makeBranch(name=u'veggies')
        self.makeBranch(name=u'packaging')

        browser = self.createRecipe(
            self.getMinimalRecipeText(branch) + "merge\n", branch=branch)
        self.assertEqual(
            'Error parsing recipe:3:6: '
            'End of line while looking for the branch id.\n'
            'Usage: merge NAME BRANCH [REVISION]',
            get_feedback_messages(browser.contents)[1])

    def test_create_recipe_no_distroseries(self):
        browser = self.getViewBrowser(
            self.makeBranchAndPackage(), '+new-recipe')
        browser.getControl(name='field.name').value = 'daily'
        browser.getControl('Description').value = 'Make some food!'
        browser.getControl(name='field.distroseries').value = []
        browser.getControl('Create Recipe').click()
        self.assertEqual(
            'You must specify at least one series for daily builds.',
            get_feedback_messages(browser.contents)[1])

    def test_create_recipe_bad_base_branch(self):
        # If a user tries to create source package recipe with a bad base
        # branch location, they should get an error.
        browser = self.createRecipe(
            self.minimal_recipe_text.splitlines()[0] + '\nfoo\n')
        # This page doesn't know whether the user was aiming for a Bazaar
        # branch or a Git repository; the error message always says
        # "branch".
        self.assertEqual(
            get_feedback_messages(browser.contents)[1],
            'foo is not a branch on Launchpad.')

    def test_create_recipe_bad_instruction_branch(self):
        # If a user tries to create source package recipe with a bad
        # instruction branch location, they should get an error.
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        branch = self.makeBranch(
            owner=self.chef, target=product, name=u'veggies')
        recipe = self.getMinimalRecipeText(branch)
        recipe += 'nest packaging foo debian'
        browser = self.createRecipe(recipe, branch)
        self.assertEqual(
            get_feedback_messages(browser.contents)[1],
            'foo %s' % self.no_such_object_message)

    def test_create_recipe_format_too_new(self):
        # If the recipe's format version is too new, we should notify the
        # user.
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        branch = self.makeBranch(
            owner=self.chef, target=product, name=u'veggies')

        with recipe_parser_newest_version(145.115):
            recipe = re.sub(
                'format [^ ]*', 'format 145.115',
                self.getMinimalRecipeText(branch))
            browser = self.createRecipe(recipe, branch)
            self.assertEqual(
                get_feedback_messages(browser.contents)[1],
                'The recipe format version specified is not available.')

    def test_create_dupe_recipe(self):
        # You shouldn't be able to create a duplicate recipe owned by the same
        # person with the same name.
        recipe = self.factory.makeSourcePackageRecipe(owner=self.chef)
        transaction.commit()
        recipe_name = recipe.name

        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        branch = self.makeBranch(
            owner=self.chef, target=product, name=u'veggies')

        # A new recipe can be created from the branch page.
        browser = self.getUserBrowser(canonical_url(branch), user=self.chef)
        browser.getLink('Create packaging recipe').click()

        browser.getControl(name='field.name').value = recipe_name
        browser.getControl('Description').value = 'Make some food!'
        browser.getControl('Secret Squirrel').click()
        browser.getControl('Create Recipe').click()

        self.assertEqual(
            get_feedback_messages(browser.contents)[1],
            'There is already a recipe owned by Master Chef with this name.')

    def test_create_recipe_private_branch(self):
        # If a user tries to create source package recipe with a private
        # base branch, they should get an error.
        branch = self.makeBranch(
            owner=self.user, information_type=InformationType.USERDATA)
        with person_logged_in(self.user):
            identity = self.getRepository(branch).identity
            recipe_text = self.getMinimalRecipeText(branch)
        browser = self.createRecipe(recipe_text)
        self.assertEqual(
            get_feedback_messages(browser.contents)[1],
            'Recipe may not refer to private %s: %s' % (
                self.branch_type, identity))

    def _test_new_recipe_with_no_related_branches(self, branch):
        # The Related Branches section should not appear if there are no
        # related branches.
        # A new recipe can be created from the branch page.
        browser = self.getUserBrowser(
            canonical_url(branch, view_name='+new-recipe'), user=self.chef)
        # There shouldn't be a related-branches section if there are no
        # related branches..
        soup = BeautifulSoup(browser.contents)
        related_branches = soup.find('fieldset', {'id': 'related-branches'})
        self.assertIs(related_branches, None)

    def test_new_product_branch_with_no_related_branches_recipe(self):
        # We can create a new recipe off a product branch.
        branch = self.makeBranch()
        self._test_new_recipe_with_no_related_branches(branch)

    def test_new_package_branch_with_no_linked_branches_recipe(self):
        # We can create a new recipe off a sourcepackage branch where the
        # sourcepackage has no linked branches.
        branch = self.makePackageBranch()
        self._test_new_recipe_with_no_related_branches(branch)

    def test_ppa_selector_not_shown_if_user_has_no_ppas(self):
        # If the user creating a recipe has no existing PPAs, the selector
        # isn't shown, but the field to enter a new PPA name is.
        self.user = self.factory.makePerson()
        branch = self.makeBranch()
        with person_logged_in(self.user):
            content = self.getMainContent(branch, '+new-recipe')
        ppa_name = content.find(attrs={'id': 'field.ppa_name'})
        self.assertEqual('input', ppa_name.name)
        self.assertEqual('text', ppa_name['type'])
        # The new ppa name field has an initial value.
        self.assertEqual('ppa', ppa_name['value'])
        ppa_chooser = content.find(attrs={'id': 'field.daily_build_archive'})
        self.assertIs(None, ppa_chooser)
        # There is a hidden option to say create a new ppa.
        ppa_options = content.find(attrs={'name': 'field.use_ppa'})
        self.assertEqual('input', ppa_options.name)
        self.assertEqual('hidden', ppa_options['type'])
        self.assertEqual('create-new', ppa_options['value'])

    def test_ppa_selector_shown_if_user_has_ppas(self):
        # If the user creating a recipe has existing PPAs, the selector is
        # shown, along with radio buttons to decide whether to use an existing
        # ppa or to create a new one.
        branch = self.makeBranch()
        with person_logged_in(self.user):
            content = self.getMainContent(branch, '+new-recipe')
        ppa_name = content.find(attrs={'id': 'field.ppa_name'})
        self.assertEqual('input', ppa_name.name)
        self.assertEqual('text', ppa_name['type'])
        # The new ppa name field has no initial value.
        self.assertEqual('', ppa_name['value'])
        ppa_chooser = content.find(attrs={'id': 'field.daily_build_archive'})
        self.assertEqual('select', ppa_chooser.name)
        ppa_options = list(
            get_radio_button_text_for_field(content, 'use_ppa'))
        self.assertEqual(
            ['(*) Use an existing PPA',
             '( ) Create a new PPA for this recipe'''],
            ppa_options)

    def test_create_new_ppa(self):
        # If the user doesn't have any PPAs, a new once can be created.
        self.user = self.factory.makePerson(name='eric')
        branch = self.makeBranch()

        # A new recipe can be created from the branch page.
        browser = self.getUserBrowser(canonical_url(branch), user=self.user)
        browser.getLink('Create packaging recipe').click()

        browser.getControl(name='field.name').value = 'name'
        browser.getControl('Description').value = 'Make some food!'
        browser.getControl('Secret Squirrel').click()
        browser.getControl('Create Recipe').click()

        # A new recipe is created in a new PPA.
        self.assertTrue(browser.url.endswith('/~eric/+recipe/name'))
        # Since no PPA name was entered, the default name (ppa) was used.
        login(ANONYMOUS)
        new_ppa = self.user.getPPAByName(self.ppa.distribution, 'ppa')
        self.assertIsNot(None, new_ppa)

    def test_create_new_ppa_duplicate(self):
        # If a new PPA is being created, and the user already has a ppa of the
        # name specifed an error is shown.
        self.user = self.factory.makePerson(name='eric')
        # Make a PPA called 'ppa' using the default.
        with person_logged_in(self.user):
            self.user.createPPA(name='foo')
        branch = self.makeBranch()

        # A new recipe can be created from the branch page.
        browser = self.getUserBrowser(canonical_url(branch), user=self.user)
        browser.getLink('Create packaging recipe').click()
        browser.getControl(name='field.name').value = 'name'
        browser.getControl('Description').value = 'Make some food!'
        browser.getControl('Secret Squirrel').click()
        browser.getControl('Create a new PPA').click()
        browser.getControl(name='field.ppa_name').value = 'foo'
        browser.getControl('Create Recipe').click()
        self.assertEqual(
            get_feedback_messages(browser.contents)[1],
            html_escape("You already have a PPA for Ubuntu named 'foo'."))

    def test_create_new_ppa_missing_name(self):
        # If a new PPA is being created, and the user has not specified a
        # name, an error is shown.
        self.user = self.factory.makePerson(name='eric')
        branch = self.makeBranch()

        # A new recipe can be created from the branch page.
        browser = self.getUserBrowser(canonical_url(branch), user=self.user)
        browser.getLink('Create packaging recipe').click()
        browser.getControl(name='field.name').value = 'name'
        browser.getControl('Description').value = 'Make some food!'
        browser.getControl('Secret Squirrel').click()
        browser.getControl(name='field.ppa_name').value = ''
        browser.getControl('Create Recipe').click()
        self.assertEqual(
            get_feedback_messages(browser.contents)[1],
            "You need to specify a name for the PPA.")

    def test_create_new_ppa_owned_by_recipe_owner(self):
        # The new PPA that is created is owned by the recipe owner.
        self.user = self.factory.makePerson(name='eric')
        team = self.factory.makeTeam(
            name='vikings', members=[self.user],
            membership_policy=TeamMembershipPolicy.MODERATED)
        with person_logged_in(team.teamowner):
            team.setMembershipData(
                self.user, TeamMembershipStatus.ADMIN, team.teamowner)
        branch = self.makeBranch(owner=team)

        # A new recipe can be created from the branch page.
        browser = self.getUserBrowser(canonical_url(branch), user=self.user)
        browser.getLink('Create packaging recipe').click()

        browser.getControl(name='field.name').value = 'name'
        browser.getControl('Description').value = 'Make some food!'
        browser.getControl(name='field.owner').value = ['vikings']
        browser.getControl('Secret Squirrel').click()
        browser.getControl('Create Recipe').click()

        # A new recipe is created in a new PPA.
        self.assertTrue(browser.url.endswith('/~vikings/+recipe/name'))
        # Since no PPA name was entered, the default name (ppa) was used.
        login(ANONYMOUS)
        new_ppa = team.getPPAByName(self.ppa.distribution, 'ppa')
        self.assertIsNot(None, new_ppa)


class TestSourcePackageRecipeAddViewBzr(
    TestSourcePackageRecipeAddViewMixin, BzrMixin, TestCaseForRecipe):

    def makeBranchAndPackage(self):
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        branch = self.factory.makeBranch(
            owner=self.chef, product=product, name='veggies')
        self.factory.makeSourcePackage(sourcepackagename='ratatouille')
        return branch

    def test_new_recipe_with_package_branches(self):
        # The series branches table should not appear if there are none.
        branch, related_series_branch_info, related_package_branches = (
            self.makeRelatedBranches(with_series_branches=False))
        browser = self.getUserBrowser(
            canonical_url(branch, view_name='+new-recipe'), user=self.chef)
        soup = BeautifulSoup(browser.contents)
        related_branches = soup.find('fieldset', {'id': 'related-branches'})
        self.assertIsNot(related_branches, None)
        related_branches = soup.find(
            'div', {'id': 'related-package-branches'})
        self.assertIsNot(related_branches, None)
        related_branches = soup.find(
            'div', {'id': 'related-series-branches'})
        self.assertIs(related_branches, None)

    def test_new_recipe_with_series_branches(self):
        # The package branches table should not appear if there are none.
        branch, related_series_branch_info, related_package_branches = (
            self.makeRelatedBranches(with_package_branches=False))
        browser = self.getUserBrowser(
            canonical_url(branch, view_name='+new-recipe'), user=self.chef)
        soup = BeautifulSoup(browser.contents)
        related_branches = soup.find('fieldset', {'id': 'related-branches'})
        self.assertIsNot(related_branches, None)
        related_branches = soup.find(
            'div', {'id': 'related-series-branches'})
        self.assertIsNot(related_branches, None)
        related_branches = soup.find(
            'div', {'id': 'related-package-branches'})
        self.assertIs(related_branches, None)

    def test_new_product_branch_recipe_with_related_branches(self):
        # The related branches should be rendered correctly on the page.
        branch, related_series_branch_info, related_package_branch_info = (
            self.makeRelatedBranches())
        browser = self.getUserBrowser(
            canonical_url(branch, view_name='+new-recipe'), user=self.chef)
        self.checkRelatedBranches(
            related_series_branch_info, related_package_branch_info,
            browser.contents)

    def test_new_sourcepackage_branch_recipe_with_related_branches(self):
        # The related branches should be rendered correctly on the page.
        reference_branch = self.makePackageBranch()
        branch, _, related_package_branch_info = (
            self.makeRelatedBranches(reference_branch))
        browser = self.getUserBrowser(
            canonical_url(branch, view_name='+new-recipe'), user=self.chef)
        self.checkRelatedBranches(
            set(), related_package_branch_info, browser.contents)


class TestSourcePackageRecipeAddViewGit(
    TestSourcePackageRecipeAddViewMixin, GitMixin, TestCaseForRecipe):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestSourcePackageRecipeAddViewGit, self).setUp()
        self.useFixture(GitHostingFixture())

    def makeBranchAndPackage(self):
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        repository = self.factory.makeGitRepository(
            owner=self.chef, target=product, name=u'veggies')
        self.factory.makeDistributionSourcePackage(
            sourcepackagename='ratatouille')
        return repository


class TestSourcePackageRecipeEditViewMixin:
    """Test the editing behaviour of a source package recipe."""

    layer = DatabaseFunctionalLayer

    def test_edit_recipe(self):
        self.factory.makeDistroSeries(
            displayname='Mumbly Midget', name='mumbly',
            distribution=self.ppa.distribution)
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        veggie_branch = self.makeBranch(
            owner=self.chef, target=product, name=u'veggies')
        meat_branch = self.makeBranch(
            owner=self.chef, target=product, name=u'meat')
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, registrant=self.chef,
            name=u'things', description=u'This is a recipe',
            distroseries=self.squirrel, branches=[veggie_branch],
            daily_build_archive=self.ppa)
        self.factory.makeArchive(
            distribution=self.ppa.distribution, name='ppa2',
            displayname="PPA 2", owner=self.chef)

        recipe_text = self.getMinimalRecipeText(meat_branch)

        browser = self.getUserBrowser(canonical_url(recipe), user=self.chef)
        browser.getLink('Edit recipe').click()
        browser.getControl(name='field.name').value = 'fings'
        browser.getControl('Description').value = 'This is stuff'
        browser.getControl('Recipe text').value = recipe_text
        browser.getControl('Secret Squirrel').click()
        browser.getControl('Mumbly Midget').click()
        browser.getControl('PPA 2').click()
        browser.getControl('Update Recipe').click()

        content = find_main_content(browser.contents)
        self.assertThat(
            'Edit This is stuff', MatchesTagText(content, 'edit-description'))
        self.assertThat(
            'Edit ' + recipe_text, MatchesTagText(content, 'edit-recipe_text'))
        self.assertThat(
            'Distribution series: Edit Mumbly Midget',
            MatchesTagText(content, 'distroseries'))
        self.assertThat(
            'PPA 2', MatchesPickerText(content, 'edit-daily_build_archive'))

    def test_edit_recipe_sets_date_last_modified(self):
        """Editing a recipe sets the date_last_modified property."""
        date_created = datetime(2000, 1, 1, 12, tzinfo=UTC)
        recipe = self.makeRecipe(date_created=date_created)

        login_person(self.chef)
        view = SourcePackageRecipeEditView(recipe, LaunchpadTestRequest())
        view.initialize()
        view.request_action.success({
            'name': u'fings',
            'recipe_text': recipe.recipe_text,
            'distroseries': recipe.distroseries})
        self.assertSqlAttributeEqualsDate(
            recipe, 'date_last_modified', UTC_NOW)

    def test_admin_edit(self):
        self.factory.makeDistroSeries(
            displayname='Mumbly Midget', name='mumbly',
            distribution=self.ppa.distribution)
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        veggie_branch = self.makeBranch(
            owner=self.chef, target=product, name=u'veggies')
        meat_branch = self.makeBranch(
            owner=self.chef, target=product, name=u'meat')
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, registrant=self.chef,
            name=u'things', description=u'This is a recipe',
            distroseries=self.squirrel, branches=[veggie_branch],
            daily_build_archive=self.ppa)

        recipe_text = self.getMinimalRecipeText(meat_branch)
        expert = getUtility(ILaunchpadCelebrities).admin.teamowner

        browser = self.getUserBrowser(canonical_url(recipe), user=expert)
        browser.getLink('Edit recipe').click()

        # There shouldn't be a daily build archive property.
        self.assertRaises(
            LookupError,
            browser.getControl,
            name='field.daily_build_archive')

        browser.getControl(name='field.name').value = 'fings'
        browser.getControl('Description').value = 'This is stuff'
        browser.getControl('Recipe text').value = recipe_text
        browser.getControl('Secret Squirrel').click()
        browser.getControl('Mumbly Midget').click()
        browser.getControl('Update Recipe').click()

        content = find_main_content(browser.contents)
        self.assertEqual('fings\nEdit', extract_text(content.h1))
        self.assertThat(
            'Edit This is stuff', MatchesTagText(content, 'edit-description'))
        self.assertThat(
            'Edit ' + recipe_text, MatchesTagText(content, 'edit-recipe_text'))
        self.assertThat(
            'Distribution series: Edit Mumbly Midget',
            MatchesTagText(content, 'distroseries'))

    def test_edit_recipe_forbidden_instruction(self):
        self.factory.makeDistroSeries(
            displayname='Mumbly Midget', name='mumbly',
            distribution=self.ppa.distribution)
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        veggie_branch = self.makeBranch(
            owner=self.chef, target=product, name=u'veggies')
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, registrant=self.chef,
            name=u'things', description=u'This is a recipe',
            distroseries=self.squirrel, branches=[veggie_branch])

        browser = self.getUserBrowser(canonical_url(recipe), user=self.chef)
        browser.getLink('Edit recipe').click()
        browser.getControl('Recipe text').value = (
            browser.getControl('Recipe text').value + 'run cat /etc/passwd')
        browser.getControl('Update Recipe').click()

        self.assertEqual(
            get_feedback_messages(browser.contents)[1],
            html_escape('The recipe instruction "run" is not permitted here.'))

    def test_edit_recipe_format_too_new(self):
        # If the recipe's format version is too new, we should notify the
        # user.
        self.factory.makeDistroSeries(
            displayname='Mumbly Midget', name='mumbly',
            distribution=self.ppa.distribution)
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        veggie_branch = self.makeBranch(
            owner=self.chef, target=product, name=u'veggies')
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, registrant=self.chef,
            name=u'things', description=u'This is a recipe',
            distroseries=self.squirrel, branches=[veggie_branch])

        new_recipe_text = re.sub(
            'format [^ ]*', 'format 145.115',
            self.getMinimalRecipeText(veggie_branch))

        with recipe_parser_newest_version(145.115):
            browser = self.getViewBrowser(recipe)
            browser.getLink('Edit recipe').click()
            browser.getControl('Recipe text').value = new_recipe_text
            browser.getControl('Update Recipe').click()

            self.assertEqual(
                get_feedback_messages(browser.contents)[1],
                'The recipe format version specified is not available.')

    def test_edit_recipe_already_exists(self):
        self.factory.makeDistroSeries(
            displayname='Mumbly Midget', name='mumbly',
            distribution=self.ppa.distribution)
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        veggie_branch = self.makeBranch(
            owner=self.chef, target=product, name=u'veggies')
        meat_branch = self.makeBranch(
            owner=self.chef, target=product, name=u'meat')
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, registrant=self.chef,
            name=u'things', description=u'This is a recipe',
            distroseries=self.squirrel, branches=[veggie_branch])
        self.factory.makeSourcePackageRecipe(
            owner=self.chef, registrant=self.chef,
            name=u'fings', description=u'This is a recipe',
            distroseries=self.squirrel, branches=[veggie_branch])

        recipe_text = self.getMinimalRecipeText(meat_branch)

        browser = self.getUserBrowser(canonical_url(recipe), user=self.chef)
        browser.getLink('Edit recipe').click()
        browser.getControl(name='field.name').value = 'fings'
        browser.getControl('Description').value = 'This is stuff'
        browser.getControl('Recipe text').value = recipe_text
        browser.getControl('Secret Squirrel').click()
        browser.getControl('Mumbly Midget').click()
        browser.getControl('Update Recipe').click()

        self.assertEqual(
            extract_text(find_tags_by_class(browser.contents, 'message')[1]),
            'There is already a recipe owned by Master Chef with this name.')

    def test_edit_recipe_private_branch(self):
        # If a user tries to set source package recipe to use a private
        # branch, they should get an error.
        recipe = self.factory.makeSourcePackageRecipe(owner=self.user)
        branch = self.makeBranch(
            owner=self.user, information_type=InformationType.USERDATA)
        with person_logged_in(self.user):
            identity = self.getRepository(branch).identity
            recipe_text = self.getMinimalRecipeText(branch)
        browser = self.getViewBrowser(recipe, '+edit')
        browser.getControl('Recipe text').value = recipe_text
        browser.getControl('Update Recipe').click()
        self.assertEqual(
            get_feedback_messages(browser.contents)[1],
            'Recipe may not refer to private %s: %s' % (
                self.branch_type, identity))

    def test_edit_recipe_no_branch(self):
        # If a user tries to set a source package recipe to use a branch
        # that isn't registered, they will get an error.
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.user, branches=[self.makeBranch()])
        no_branch_recipe_text = (
            recipe.recipe_text.splitlines()[0] + "\nlp:nonexistent\n")
        browser = self.getViewBrowser(recipe, '+edit')
        browser.getControl('Recipe text').value = no_branch_recipe_text
        browser.getControl('Update Recipe').click()
        self.assertEqual(
            get_feedback_messages(browser.contents)[1],
            'lp:nonexistent %s' % self.no_such_object_message)

    def _test_edit_recipe_with_no_related_branches(self, recipe):
        # The Related Branches section should not appear if there are no
        # related branches.
        browser = self.getUserBrowser(canonical_url(recipe), user=self.chef)
        browser.getLink('Edit recipe').click()
        # There shouldn't be a related-branches section if there are no
        # related branches.
        soup = BeautifulSoup(browser.contents)
        related_branches = soup.find('fieldset', {'id': 'related-branches'})
        self.assertIs(related_branches, None)

    def test_edit_product_branch_with_no_related_branches_recipe(self):
        # The Related Branches section should not appear if there are no
        # related branches.
        base_branch = self.makeBranch()
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, branches=[base_branch])
        self._test_edit_recipe_with_no_related_branches(recipe)

    def test_edit_sourcepackage_branch_with_no_related_branches_recipe(self):
        # The Related Branches section should not appear if there are no
        # related branches.
        base_branch = self.makePackageBranch()
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, branches=[base_branch])
        self._test_edit_recipe_with_no_related_branches(recipe)


class TestSourcePackageRecipeEditViewBzr(
    TestSourcePackageRecipeEditViewMixin, BzrMixin, TestCaseForRecipe):

    def test_edit_recipe_with_package_branches(self):
        # The series branches table should not appear if there are none.
        with person_logged_in(self.chef):
            base_branch = self.makeBranch()
            recipe = self.factory.makeSourcePackageRecipe(
                owner=self.chef, branches=[base_branch])
            self.makeRelatedBranches(
                reference_branch=base_branch, with_series_branches=False)
        browser = self.getUserBrowser(canonical_url(recipe), user=self.chef)
        browser.getLink('Edit recipe').click()
        soup = BeautifulSoup(browser.contents)
        related_branches = soup.find('fieldset', {'id': 'related-branches'})
        self.assertIsNot(related_branches, None)
        related_branches = soup.find(
            'div', {'id': 'related-package-branches'})
        self.assertIsNot(related_branches, None)
        related_branches = soup.find(
            'div', {'id': 'related-series-branches'})
        self.assertIs(related_branches, None)

    def test_edit_recipe_with_series_branches(self):
        # The package branches table should not appear if there are none.
        with person_logged_in(self.chef):
            base_branch = self.makeBranch()
            recipe = self.factory.makeSourcePackageRecipe(
                owner=self.chef, branches=[base_branch])
            self.makeRelatedBranches(
                reference_branch=base_branch, with_package_branches=False)
        browser = self.getUserBrowser(canonical_url(recipe), user=self.chef)
        browser.getLink('Edit recipe').click()
        soup = BeautifulSoup(browser.contents)
        related_branches = soup.find('fieldset', {'id': 'related-branches'})
        self.assertIsNot(related_branches, None)
        related_branches = soup.find(
            'div', {'id': 'related-series-branches'})
        self.assertIsNot(related_branches, None)
        related_branches = soup.find(
            'div', {'id': 'related-package-branches'})
        self.assertIs(related_branches, None)

    def test_edit_product_branch_recipe_with_related_branches(self):
        # The related branches should be rendered correctly on the page.
        with person_logged_in(self.chef):
            base_branch = self.makeBranch()
            recipe = self.factory.makeSourcePackageRecipe(
                owner=self.chef, branches=[base_branch])
            _, related_series_branch_info, related_package_branch_info = (
                self.makeRelatedBranches(reference_branch=base_branch))
        browser = self.getUserBrowser(
            canonical_url(recipe, view_name='+edit'), user=self.chef)
        self.checkRelatedBranches(
            related_series_branch_info, related_package_branch_info,
            browser.contents)

    def test_edit_sourcepackage_branch_recipe_with_related_branches(self):
        # The related branches should be rendered correctly on the page.
        with person_logged_in(self.chef):
            reference_branch = self.makePackageBranch()
            recipe = self.factory.makeSourcePackageRecipe(
                    owner=self.chef, branches=[reference_branch])
            _, _, related_package_branch_info = (
                self.makeRelatedBranches(reference_branch))
        browser = self.getUserBrowser(
            canonical_url(recipe, view_name='+edit'), user=self.chef)
        self.checkRelatedBranches(
            set(), related_package_branch_info, browser.contents)


class TestSourcePackageRecipeEditViewGit(
    TestSourcePackageRecipeEditViewMixin, GitMixin, TestCaseForRecipe):
    pass


class TestSourcePackageRecipeViewMixin:

    layer = LaunchpadFunctionalLayer

    def makeSuccessfulBuild(self, archive=None):
        if archive is None:
            archive = self.ppa
        recipe = self.makeRecipe()
        build = self.factory.makeSourcePackageRecipeBuild(
            recipe=recipe, distroseries=self.squirrel, archive=archive)
        build.updateStatus(
            BuildStatus.BUILDING,
            date_started=datetime(2010, 3, 16, tzinfo=UTC))
        build.updateStatus(
            BuildStatus.FULLYBUILT,
            date_finished=datetime(2010, 3, 16, tzinfo=UTC))
        return build

    def test_index(self):
        build = self.makeSuccessfulBuild()
        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Recipes cake_recipe
            .*
            Description Edit
            This recipe .*changes.

            Recipe information
            Build schedule: .* Built on request Edit
            Owner: Master Chef Edit
            Base source: lp:.*~chef/chocolate.*cake
            Debian version: {debupstream}-0~{rev.*}
            Daily build archive: Secret PPA Edit
            Distribution series: Edit Secret Squirrel

            Latest builds
            Status When complete Distribution series Archive
            Successful build on 2010-03-16 Secret Squirrel Secret PPA
            Request build\(s\)

            Recipe contents Edit
            # .* format .* deb-version {debupstream}-0~{rev.*}
            lp:.*~chef/chocolate.*cake.*""", self.getMainText(build.recipe))

    def test_index_success_with_buildlog(self):
        # The buildlog is shown if it is there.
        build = self.makeSuccessfulBuild()
        build.setLog(self.factory.makeLibraryFileAlias())

        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Latest builds
            Status .* Archive
            Successful build on 2010-03-16 buildlog \(.*\)
                Secret Squirrel Secret PPA
            Request build\(s\)""", self.getMainText(build.recipe))

    def test_index_success_with_binary_builds(self):
        # Binary builds are shown after the recipe builds if there are any.
        build = self.makeSuccessfulBuild()
        build.setLog(self.factory.makeLibraryFileAlias())
        package_name = self.factory.getOrMakeSourcePackageName('chocolate')
        source_package_release = self.factory.makeSourcePackageRelease(
            archive=self.ppa, sourcepackagename=package_name,
            distroseries=self.squirrel, source_package_recipe_build=build,
            version='0+r42')
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=source_package_release, archive=self.ppa,
            distroseries=self.squirrel)
        builder = self.factory.makeBuilder()
        binary_build = self.factory.makeBinaryPackageBuild(
            source_package_release=source_package_release,
            distroarchseries=self.squirrel.nominatedarchindep,
            processor=builder.processor)
        binary_build.queueBuild()

        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Latest builds
            Status .* Archive
            Successful build on 2010-03-16 buildlog \(.*\)
               Secret Squirrel Secret PPA chocolate - 0\+r42 in .*
               \(estimated\) i386
            Request build\(s\)""", self.getMainText(build.recipe))

    def test_index_success_with_completed_binary_build(self):
        # Binary builds show their buildlog too.
        build = self.makeSuccessfulBuild()
        build.setLog(self.factory.makeLibraryFileAlias())
        package_name = self.factory.getOrMakeSourcePackageName('chocolate')
        source_package_release = self.factory.makeSourcePackageRelease(
            archive=self.ppa, sourcepackagename=package_name,
            distroseries=self.squirrel, source_package_recipe_build=build,
            version='0+r42')
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=source_package_release, archive=self.ppa,
            distroseries=self.squirrel)
        builder = self.factory.makeBuilder()
        binary_build = self.factory.makeBinaryPackageBuild(
                source_package_release=source_package_release,
                distroarchseries=self.squirrel.nominatedarchindep,
                processor=builder.processor)
        binary_build.queueBuild()
        binary_build.updateStatus(
            BuildStatus.BUILDING,
            date_started=datetime(2010, 4, 16, tzinfo=UTC))
        binary_build.updateStatus(
            BuildStatus.FULLYBUILT,
            date_finished=datetime(2010, 4, 16, tzinfo=UTC))
        binary_build.setLog(self.factory.makeLibraryFileAlias())

        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Latest builds
            Status .* Archive
            Successful build on 2010-03-16 buildlog \(.*\) Secret Squirrel
              Secret PPA chocolate - 0\+r42 on 2010-04-16 buildlog \(.*\) i386
            Request build\(s\)""", self.getMainText(build.recipe))

    def test_index_success_with_sprb_into_private_ppa(self):
        # The index page hides builds into archives the user can't view.
        archive = self.factory.makeArchive(private=True)
        with admin_logged_in():
            build = self.makeSuccessfulBuild(archive=archive)
            self.assertIn(
                "This recipe has not been built yet.",
                self.getMainText(build.recipe))

    def test_index_no_builds(self):
        """A message should be shown when there are no builds."""
        recipe = self.makeRecipe()
        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Latest builds
            Status .* Archive
            This recipe has not been built yet.""", self.getMainText(recipe))

    def test_index_no_suitable_builders(self):
        recipe = self.makeRecipe()
        self.factory.makeSourcePackageRecipeBuild(
            recipe=recipe, distroseries=self.squirrel, archive=self.ppa)
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            Latest builds
            Status .* Archive
            No suitable builders Secret Squirrel Secret PPA
            Request build\(s\)""", self.getMainText(recipe))

    def makeBuildJob(self, recipe, date_created=None):
        """Return a build associated with a buildjob."""
        build = self.factory.makeSourcePackageRecipeBuild(
            recipe=recipe, distroseries=self.squirrel, archive=self.ppa,
            date_created=date_created)
        build.queueBuild()
        return build

    def test_index_pending(self):
        """Test the listing of a pending build."""
        recipe = self.makeRecipe()
        self.makeBuildJob(recipe)
        self.factory.makeBuilder()
        pattern = """\
            Latest builds
            Status .* Archive
            Pending build in .* \(estimated\) Secret Squirrel Secret PPA
            Request build\(s\)

            Recipe contents"""
        main_text = self.getMainText(recipe)
        self.assertTextMatchesExpressionIgnoreWhitespace(
            pattern, main_text)

    def test_builds(self):
        """Ensure SourcePackageRecipeView.builds is as described."""
        recipe = self.makeRecipe()
        # We create builds in time ascending order (oldest first) since we
        # use id as the ordering attribute and lower ids mean created earlier.
        date_gen = time_counter(
            datetime(2010, 3, 16, tzinfo=UTC), timedelta(days=1))
        build1 = self.makeBuildJob(recipe, date_gen.next())
        build2 = self.makeBuildJob(recipe, date_gen.next())
        build3 = self.makeBuildJob(recipe, date_gen.next())
        build4 = self.makeBuildJob(recipe, date_gen.next())
        build5 = self.makeBuildJob(recipe, date_gen.next())
        build6 = self.makeBuildJob(recipe, date_gen.next())
        view = SourcePackageRecipeView(recipe, None)
        self.assertEqual(
            [build6, build5, build4, build3, build2, build1],
            view.builds)

        def set_status(build, status):
            build.updateStatus(
                BuildStatus.BUILDING, date_started=build.date_created)
            build.updateStatus(
                status,
                date_finished=build.date_created + timedelta(minutes=10))
        set_status(build6, BuildStatus.FULLYBUILT)
        set_status(build5, BuildStatus.FAILEDTOBUILD)
        # When there are 4+ pending builds, only the most
        # recently-completed build is returned (i.e. build1, not build2)
        self.assertEqual(
            [build4, build3, build2, build1, build6],
            view.builds)
        set_status(build4, BuildStatus.FULLYBUILT)
        set_status(build3, BuildStatus.FULLYBUILT)
        set_status(build2, BuildStatus.FULLYBUILT)
        set_status(build1, BuildStatus.FULLYBUILT)
        self.assertEqual(
            [build6, build5, build4, build3, build2], view.builds)

    def test_request_builds_redirects_on_get(self):
        recipe = self.makeRecipe(is_stale=True, build_daily=True)
        with person_logged_in(self.chef):
            url = canonical_url(recipe)
        browser = self.getViewBrowser(recipe, '+request-daily-build')
        self.assertEqual(url, browser.url)

    def test_request_daily_builds_button_stale(self):
        # Recipes that are stale and are built daily have a build now link
        recipe = self.makeRecipe(is_stale=True, build_daily=True)
        browser = self.getViewBrowser(recipe)
        build_button = find_tag_by_id(browser.contents, 'field.actions.build')
        self.assertIsNot(None, build_button)

    def test_request_daily_builds_button_not_stale(self):
        # Recipes that are not stale do not have a build now link
        login(ANONYMOUS)
        recipe = self.makeRecipe(is_stale=False, build_daily=True)
        browser = self.getViewBrowser(recipe)
        build_button = find_tag_by_id(browser.contents, 'field.actions.build')
        self.assertIs(None, build_button)

    def test_request_daily_builds_button_not_daily(self):
        # Recipes that are not built daily do not have a build now link
        login(ANONYMOUS)
        recipe = self.makeRecipe(is_stale=True, build_daily=False)
        browser = self.getViewBrowser(recipe)
        build_button = find_tag_by_id(browser.contents, 'field.actions.build')
        self.assertIs(None, build_button)

    def test_request_daily_builds_button_no_daily_ppa(self):
        # Recipes that have no daily build ppa do not have a build now link
        login(ANONYMOUS)
        branch = self.makeBranch()
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, branches=[branch],
            is_stale=True, build_daily=True)
        naked_recipe = removeSecurityProxy(recipe)
        naked_recipe.daily_build_archive = None
        browser = self.getViewBrowser(recipe)
        build_button = find_tag_by_id(browser.contents, 'field.actions.build')
        self.assertIs(None, build_button)

    def test_request_daily_builds_button_no_recipe_permission(self):
        # Recipes do not have a build now link if the user does not have edit
        # permission on the recipe.
        login(ANONYMOUS)
        recipe = self.makeRecipe(is_stale=True, build_daily=True)
        person = self.factory.makePerson()
        browser = self.getViewBrowser(recipe, user=person)
        build_button = find_tag_by_id(browser.contents, 'field.actions.build')
        self.assertIs(None, build_button)

    def test_request_daily_builds_button_ppa_with_no_permissions(self):
        # Recipes that have a daily build ppa without upload permissions
        # do not have a build now link
        login(ANONYMOUS)
        distroseries = self.factory.makeSourcePackageRecipeDistroseries()
        person = self.factory.makePerson()
        branch = self.makeBranch()
        daily_build_archive = self.factory.makeArchive(
            distribution=distroseries.distribution, owner=person)
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, branches=[branch],
            daily_build_archive=daily_build_archive,
            is_stale=True, build_daily=True)
        browser = self.getViewBrowser(recipe)
        build_button = find_tag_by_id(browser.contents, 'field.actions.build')
        self.assertIs(None, build_button)

    def test_request_daily_builds_button_ppa_disabled(self):
        # Recipes whose daily build ppa is disabled do not have a build now
        # link.
        distroseries = self.factory.makeSourcePackageRecipeDistroseries()
        branch = self.makeBranch()
        daily_build_archive = self.factory.makeArchive(
            distribution=distroseries.distribution, owner=self.user)
        with person_logged_in(self.user):
            daily_build_archive.disable()
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, branches=[branch],
            daily_build_archive=daily_build_archive,
            is_stale=True, build_daily=True)
        browser = self.getViewBrowser(recipe)
        build_button = find_tag_by_id(browser.contents, 'field.actions.build')
        self.assertIs(None, build_button)

    def test_request_daily_builds_ajax_link_not_rendered(self):
        # The Build now link should not be rendered without javascript.
        recipe = self.makeRecipe(is_stale=True, build_daily=True)
        browser = self.getViewBrowser(recipe)
        build_link = find_tag_by_id(browser.contents, 'request-daily-builds')
        self.assertIs(None, build_link)

    def test_request_daily_builds_action(self):
        # Daily builds should be triggered when requested.
        branch = self.makeBranch()
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, branches=[branch], daily_build_archive=self.ppa,
            is_stale=True, build_daily=True)
        browser = self.getViewBrowser(recipe)
        browser.getControl('Build now').click()
        login(ANONYMOUS)
        builds = recipe.pending_builds
        build_distros = [
            build.distroseries.displayname for build in builds]
        build_distros.sort()
        # Our recipe has a Warty distroseries
        self.assertEqual(['Warty'], build_distros)
        self.assertEqual(
            set([2510]),
            set(build.buildqueue_record.lastscore for build in builds))

    def test_request_daily_builds_disabled_archive(self):
        # Requesting a daily build from a disabled archive is a user error.
        recipe = self.makeRecipe(is_stale=True, build_daily=True)
        harness = LaunchpadFormHarness(
            recipe, SourcePackageRecipeRequestDailyBuildView)
        with person_logged_in(self.ppa.owner):
            self.ppa.disable()
        harness.submit('build', {})
        self.assertEqual(
            "Secret PPA is disabled.",
            harness.view.request.notifications[0].message)

    def test_request_daily_builds_obsolete_series(self):
        # Requesting a daily build with an obsolete series gives a warning.
        recipe = self.makeRecipe(is_stale=True, build_daily=True)
        warty = self.factory.makeSourcePackageRecipeDistroseries()
        hoary = self.factory.makeSourcePackageRecipeDistroseries(name='hoary')
        with person_logged_in(self.chef):
            recipe.updateSeries((warty, hoary))
        removeSecurityProxy(warty).status = SeriesStatus.OBSOLETE
        harness = LaunchpadFormHarness(
            recipe, SourcePackageRecipeRequestDailyBuildView)
        harness.submit('build', {})
        self.assertEqual(
            '1 new recipe build has been queued.<p>The recipe contains an '
            'obsolete distroseries, which has been skipped.</p>',
            harness.view.request.notifications[0].message)

    def test_request_builds_page(self):
        """Ensure the +request-builds page is sane."""
        recipe = self.makeRecipe()
        pattern = dedent("""\
            Request builds for cake_recipe
            Recipes
            cake_recipe
            Request builds for cake_recipe
            Archive:
            (nothing selected)
            Secret PPA [~chef/ubuntu/ppa]
            Distribution series:
            Secret Squirrel
            Hoary
            Warty
            or
            Cancel""")
        main_text = self.getMainText(recipe, '+request-builds')
        self.assertEqual(pattern, main_text)

    def test_request_builds_action(self):
        """Requesting a build creates pending builds."""
        self._makeWoodyDistroSeries()
        recipe = self.makeRecipe()
        browser = self.getViewBrowser(recipe, '+request-builds')
        browser.getControl('Woody').click()
        browser.getControl('Request builds').click()

        login(ANONYMOUS)
        builds = recipe.pending_builds
        build_distros = [
            build.distroseries.displayname for build in builds]
        build_distros.sort()
        # Secret Squirrel is checked by default.
        self.assertEqual(['Secret Squirrel', 'Woody'], build_distros)
        build_scores = [build.buildqueue_record.lastscore for build in builds]
        self.assertContentEqual([2610, 2610], build_scores)

    def test_request_builds_action_not_logged_in(self):
        """Requesting a build creates pending builds."""
        self.useFixture(FakeLogger())
        self._makeWoodyDistroSeries()
        recipe = self.makeRecipe()
        browser = self.getViewBrowser(recipe, no_login=True)
        self.assertRaises(
            Unauthorized, browser.getLink('Request build(s)').click)

    def test_request_builds_archive_no_daily_build_archive(self):
        branch = self.makeBranch()
        recipe = self.factory.makeSourcePackageRecipe(branches=[branch])
        view = SourcePackageRecipeRequestBuildsView(recipe, None)
        self.assertIs(None, view.initial_values.get('archive'))

    def test_request_builds_archive_daily_build_archive_unuploadable(self):
        branch = self.makeBranch()
        ppa = self.factory.makeArchive()
        recipe = self.factory.makeSourcePackageRecipe(
            branches=[branch], daily_build_archive=ppa)
        with person_logged_in(self.chef):
            view = SourcePackageRecipeRequestBuildsView(recipe, None)
            self.assertIs(None, view.initial_values.get('archive'))

    def test_request_builds_archive(self):
        branch = self.makeBranch()
        ppa = self.factory.makeArchive(
            displayname='Secret PPA', owner=self.chef, name='ppa2')
        recipe = self.factory.makeSourcePackageRecipe(
            branches=[branch], daily_build_archive=ppa)
        with person_logged_in(self.chef):
            view = SourcePackageRecipeRequestBuildsView(recipe, None)
            self.assertEqual(ppa, view.initial_values.get('archive'))

    def _makeWoodyDistroSeries(self):
        woody = self.factory.makeDistroSeries(
            name='woody', displayname='Woody',
            distribution=self.ppa.distribution)
        removeSecurityProxy(woody).nominatedarchindep = woody.newArch(
            'i386', getUtility(IProcessorSet).getByName('386'), False,
            self.factory.makePerson())
        return woody

    def test_request_builds_rejects_duplicate(self):
        """Duplicate build requests cause validation failures."""
        woody = self._makeWoodyDistroSeries()
        recipe = self.makeRecipe()
        recipe.requestBuild(
            self.ppa, self.chef, woody, PackagePublishingPocket.RELEASE)

        browser = self.getViewBrowser(recipe, '+request-builds')
        browser.getControl('Woody').click()
        browser.getControl('Request builds').click()
        self.assertIn(
            "An identical build is already pending for ubuntu woody.",
            extract_text(find_main_content(browser.contents)))

    def makeRecipeWithUploadIssues(self):
        """Make a recipe where the owner can't upload to the PPA."""
        # This occurs when the PPA that the recipe is being built daily into
        # is owned by a team, and the owner of the recipe isn't in the team
        # that owns the PPA.
        registrant = self.factory.makePerson()
        owner_team = self.factory.makeTeam(members=[registrant], name='team1')
        branch = self.makeBranch()
        ppa_team = self.factory.makeTeam(members=[registrant], name='team2')
        ppa = self.factory.makeArchive(owner=ppa_team, name='ppa')
        return self.factory.makeSourcePackageRecipe(
            registrant=registrant, owner=owner_team, branches=[branch],
            daily_build_archive=ppa, build_daily=True)

    def test_owner_with_no_ppa_upload_permission(self):
        # Daily build with upload issues are a problem.
        recipe = self.makeRecipeWithUploadIssues()
        view = create_initialized_view(recipe, '+index')
        self.assertTrue(view.dailyBuildWithoutUploadPermission())

    def test_owner_with_no_ppa_upload_permission_non_daily(self):
        # Non-daily builds with upload issues are not so much of an issue.
        recipe = self.makeRecipeWithUploadIssues()
        with person_logged_in(recipe.registrant):
            recipe.build_daily = False
        view = create_initialized_view(recipe, '+index')
        self.assertFalse(view.dailyBuildWithoutUploadPermission())

    def test_owner_with_no_ppa_upload_permission_message(self):
        # If there is an issue, a message is shown.
        recipe = self.makeRecipeWithUploadIssues()
        browser = self.getViewBrowser(recipe, '+index')
        messages = get_feedback_messages(browser.contents)
        self.assertEqual(
            "Daily builds for this recipe will not occur.\n"
            "The owner of the recipe (Team1) does not have permission to "
            "upload packages into the daily build PPA (PPA for Team2)",
            messages[-1])

    def test_view_with_disabled_archive(self):
        # When a PPA is disabled, it is only viewable to the owner. This
        # case is handled with the view not showing builds into a disabled
        # archive, rather than giving an Unauthorized error to the user.
        branch = self.makeBranch()
        recipe = self.factory.makeSourcePackageRecipe(
            branches=[branch], build_daily=True)
        recipe.requestBuild(
            recipe.daily_build_archive, recipe.owner, self.squirrel,
            PackagePublishingPocket.RELEASE)
        with person_logged_in(recipe.owner):
            recipe.daily_build_archive.disable()
        browser = self.getUserBrowser(canonical_url(recipe))
        self.assertIn(
            "This recipe has not been built yet.",
            extract_text(find_main_content(browser.contents)))


class TestSourcePackageRecipeViewBzr(
    TestSourcePackageRecipeViewMixin, BzrMixin, TestCaseForRecipe):
    pass


class TestSourcePackageRecipeViewGit(
    TestSourcePackageRecipeViewMixin, GitMixin, TestCaseForRecipe):
    pass


class TestSourcePackageRecipeBuildViewMixin:
    """Test behaviour of SourcePackageRecipeBuildView."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        """Provide useful defaults."""
        super(TestSourcePackageRecipeBuildViewMixin, self).setUp()
        self.user = self.factory.makePerson(
            displayname='Owner', name='build-owner')

    def makeBuild(self):
        """Make a build suitable for testing."""
        archive = self.factory.makeArchive(name='build',
            owner=self.user)
        branch = self.makeBranch()
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.user, name=u'my-recipe', branches=[branch])
        distro_series = self.factory.makeDistroSeries(
            name='squirrel', distribution=archive.distribution)
        removeSecurityProxy(distro_series).nominatedarchindep = (
            self.factory.makeDistroArchSeries(
                distroseries=distro_series,
                processor=getUtility(IProcessorSet).getByName('386')))
        build = self.factory.makeSourcePackageRecipeBuild(
            requester=self.user, archive=archive, recipe=recipe,
            distroseries=distro_series)
        build.queueBuild()
        self.factory.makeBuilder()
        return build

    def makeBuildView(self):
        """Return a view of a build suitable for testing."""
        return SourcePackageRecipeBuildView(self.makeBuild(), None)

    def test_estimate(self):
        """Time should be estimated until the job is completed."""
        view = self.makeBuildView()
        self.assertTrue(view.estimate)
        view.context.updateStatus(BuildStatus.BUILDING)
        clear_property_cache(view)
        self.assertTrue(view.estimate)
        view.context.updateStatus(BuildStatus.FULLYBUILT)
        clear_property_cache(view)
        self.assertFalse(view.estimate)

    def test_eta(self):
        """ETA should be reasonable.

        It should be None if there is no builder or queue entry.
        It should be getEstimatedJobStartTime + estimated duration for jobs
        that have not started.
        It should be bq.date_started + estimated duration for jobs that have
        started.
        """
        branch = self.makeBranch()
        recipe = self.factory.makeSourcePackageRecipe(branches=[branch])
        build = self.factory.makeSourcePackageRecipeBuild(recipe=recipe)
        view = SourcePackageRecipeBuildView(build, None)
        self.assertIs(None, view.eta)
        queue_entry = removeSecurityProxy(build.queueBuild())
        queue_entry._now = lambda: datetime(1970, 1, 1, 0, 0, 0, 0, UTC)
        self.factory.makeBuilder(
            processors=[queue_entry.processor], virtualized=True)
        clear_property_cache(view)
        self.assertIsNot(None, view.eta)
        self.assertEqual(
            queue_entry.getEstimatedJobStartTime() +
            queue_entry.estimated_duration, view.eta)
        queue_entry.markAsBuilding(None)
        clear_property_cache(view)
        self.assertEqual(
            queue_entry.date_started + queue_entry.estimated_duration,
            view.eta)

    def getBuildBrowser(self, build, view_name=None):
        """Return a browser for the specified build, opened as owner."""
        login(ANONYMOUS)
        url = canonical_url(build, view_name=view_name)
        return self.getUserBrowser(url, self.build_owner)

    def test_render_index(self):
        """Test the basic index page."""
        main_text = self.getMainText(self.makeBuild(), '+index')
        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            created .*
            Build status
            Needs building
            Start in .* \\(2510\\) What's this?.*
            Estimated finish in .*
            Build details
            Recipe:        Recipe my-recipe for Owner
            Archive:       PPA named build for Owner
            Series:        Squirrel
            Pocket:        Release
            Binary builds: None""", main_text)

    def test_render_index_completed(self):
        """Test the index page of a completed build."""
        release = self.makeBuildAndRelease()
        self.makeBinaryBuild(release, 'itanic')
        build = release.source_package_recipe_build
        build.updateStatus(
            BuildStatus.BUILDING,
            date_started=datetime(2009, 1, 1, tzinfo=UTC))
        build.updateStatus(
            BuildStatus.FULLYBUILT,
            date_finished=build.date_started + timedelta(minutes=1))
        build.buildqueue_record.destroySelf()
        build.setLog(self.factory.makeLibraryFileAlias(content='buildlog'))
        build.storeUploadLog('upload_log')
        main_text = self.getMainText(
            release.source_package_recipe_build, '+index')
        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            created .*
            Build status
            Successfully built
            Started on .*
            Finished on .*
            \(took 1 minute, 0.0 seconds\)
            buildlog \(8 bytes\)
            uploadlog \(10 bytes\)
            Build details
            Recipe:        Recipe my-recipe for Owner
            Archive:       PPA named build for Owner
            Series:        Squirrel
            Pocket:        Release
            Binary builds:
            itanic build of .* 3.14 in ubuntu squirrel RELEASE""",
            main_text)

    def makeBuildAndRelease(self):
        """Make a build and release suitable for testing."""
        build = self.makeBuild()
        multiverse = self.factory.makeComponent(name='multiverse')
        return self.factory.makeSourcePackageRelease(
            source_package_recipe_build=build, version='3.14',
            component=multiverse)

    def makeBinaryBuild(self, release, architecturetag):
        """Make a binary build with specified release and architecturetag."""
        distroarchseries = self.factory.makeDistroArchSeries(
            architecturetag=architecturetag,
            distroseries=release.upload_distroseries,
            processor=self.factory.makeProcessor())
        return self.factory.makeBinaryPackageBuild(
            source_package_release=release, distroarchseries=distroarchseries)

    def test_render_binary_builds(self):
        """BinaryBuilds for this source build are shown if they exist."""
        release = self.makeBuildAndRelease()
        self.makeBinaryBuild(release, 'itanic')
        self.makeBinaryBuild(release, 'x87-64')
        main_text = self.getMainText(
            release.source_package_recipe_build, '+index')
        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Binary builds:
            itanic build of .* 3.14 in ubuntu squirrel RELEASE
            x87-64 build of .* 3.14 in ubuntu squirrel RELEASE$""",
            main_text)

    def test_logtail(self):
        """Logtail is shown for BUILDING builds."""
        build = self.makeBuild()
        build.buildqueue_record.logtail = 'Logs have no tails!'
        build.buildqueue_record.builder = self.factory.makeBuilder()
        main_text = self.getMainText(build, '+index')
        self.assertNotIn('Logs have no tails!', main_text)
        with admin_logged_in():
            build.updateStatus(BuildStatus.BUILDING)
        main_text = self.getMainText(build, '+index')
        self.assertIn('Logs have no tails!', main_text)
        with admin_logged_in():
            build.updateStatus(BuildStatus.FULLYBUILT)
        self.assertIn('Logs have no tails!', main_text)

    def getMainText(self, build, view_name=None):
        """Return the main text of a view's web page."""
        browser = self.getViewBrowser(build, '+index')
        return extract_text(find_main_content(browser.contents))

    def test_buildlog(self):
        """A link to the build log is shown if available."""
        build = self.makeBuild()
        build.setLog(self.factory.makeLibraryFileAlias())
        build_log_url = build.log_url
        browser = self.getViewBrowser(build)
        link = browser.getLink('buildlog')
        self.assertEqual(build_log_url, link.url)

    def test_uploadlog(self):
        """A link to the upload log is shown if available."""
        build = self.makeBuild()
        build.storeUploadLog('uploaded')
        upload_log_url = build.upload_log_url
        browser = self.getViewBrowser(build)
        link = browser.getLink('uploadlog')
        self.assertEqual(upload_log_url, link.url)


class TestSourcePackageRecipeBuildViewBzr(
    TestSourcePackageRecipeBuildViewMixin, BzrMixin, BrowserTestCase):
    pass


class TestSourcePackageRecipeBuildViewGit(
    TestSourcePackageRecipeBuildViewMixin, GitMixin, BrowserTestCase):
    pass


class TestSourcePackageRecipeDeleteViewMixin:

    layer = DatabaseFunctionalLayer

    def test_delete_recipe(self):
        branch = self.makeBranch()
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, branches=[branch])

        browser = self.getUserBrowser(
            canonical_url(recipe), user=self.chef)

        browser.getLink('Delete recipe').click()
        browser.getControl('Delete recipe').click()

        self.assertEqual(
            'http://code.launchpad.dev/~chef',
            browser.url)

    def test_delete_recipe_no_permissions(self):
        self.useFixture(FakeLogger())
        branch = self.makeBranch()
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, branches=[branch])
        nopriv_person = self.factory.makePerson()
        recipe_url = canonical_url(recipe)

        browser = self.getUserBrowser(
            recipe_url, user=nopriv_person)

        self.assertRaises(
            LinkNotFoundError,
            browser.getLink, 'Delete recipe')

        self.assertRaises(
            Unauthorized,
            self.getUserBrowser, recipe_url + '/+delete', user=nopriv_person)


class TestSourcePackageRecipeDeleteViewBzr(
    TestSourcePackageRecipeDeleteViewMixin, BzrMixin, TestCaseForRecipe):
    pass


class TestSourcePackageRecipeDeleteViewGit(
    TestSourcePackageRecipeDeleteViewMixin, GitMixin, TestCaseForRecipe):
    pass


class TestBrokenExistingRecipesMixin:
    """Existing recipes broken by builder updates need to be editable.

    This happened with a 0.2 -> 0.3 release where the nest command was no
    longer allowed to refer the '.'.  There were already existing recipes that
    had this text that were not viewable or editable.  This test case captures
    that and makes sure the views stay visible.
    """

    layer = LaunchpadFunctionalLayer

    def makeBrokenRecipe(self):
        """Make a valid recipe, then break it."""
        product = self.factory.makeProduct()
        b1 = self.makeBranch(target=product)
        b2 = self.makeBranch(target=product)
        recipe_text = dedent("""\
            %s
            %s
            nest name %s foo
            """ % (self.RECIPE_FIRST_LINE, self.getBranchRecipeText(b1),
                   self.getRepository(b2).identity))
        recipe = self.factory.makeSourcePackageRecipe(recipe=recipe_text)
        naked_data = removeSecurityProxy(recipe)._recipe_data
        nest_instruction = list(naked_data.instructions)[0]
        nest_instruction.directory = u'.'
        return recipe

    def test_recipe_is_broken(self):
        recipe = self.makeBrokenRecipe()
        self.assertRaises(Exception, str, recipe.builder_recipe)

    def assertRecipeInText(self, text):
        """If the first line is shown, that's good enough for us."""
        self.assertTrue(self.RECIPE_FIRST_LINE in text)

    def test_recipe_index_renderable(self):
        recipe = self.makeBrokenRecipe()
        main_text = self.getMainText(recipe, '+index')
        self.assertRecipeInText(main_text)

    def test_recipe_edit_renderable(self):
        recipe = self.makeBrokenRecipe()
        main_text = self.getMainText(recipe, '+edit', user=recipe.owner)
        self.assertRecipeInText(main_text)


class TestBrokenExistingRecipesBzr(
    TestBrokenExistingRecipesMixin, BzrMixin, BrowserTestCase):

    RECIPE_FIRST_LINE = (
        "# bzr-builder format 0.2 deb-version {debupstream}+{revno}")


class TestBrokenExistingRecipesGit(
    TestBrokenExistingRecipesMixin, GitMixin, BrowserTestCase):

    RECIPE_FIRST_LINE = (
        "# git-build-recipe format 0.4 deb-version {debupstream}+{revtime}")
