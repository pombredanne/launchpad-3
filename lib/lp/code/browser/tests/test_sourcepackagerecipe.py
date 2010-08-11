# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
# pylint: disable-msg=F0401,E1002

"""Tests for the source package recipe view classes and templates."""

from __future__ import with_statement

__metaclass__ = type


from datetime import datetime, timedelta
from textwrap import dedent

import transaction
from pytz import utc
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.testing.pages import (
    extract_text, find_main_content, find_tags_by_class)
from canonical.testing import (
    DatabaseFunctionalLayer, LaunchpadFunctionalLayer)
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.code.browser.sourcepackagerecipe import (
    SourcePackageRecipeView, SourcePackageRecipeRequestBuildsView)
from lp.code.browser.sourcepackagerecipebuild import (
    SourcePackageRecipeBuildView)
from lp.code.interfaces.sourcepackagerecipe import MINIMAL_RECIPE_TEXT
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.model.processor import ProcessorFamily
from lp.testing import (
    ANONYMOUS, BrowserTestCase, login, logout, person_logged_in)
from lp.testing.factory import remove_security_proxy_and_shout_at_engineer


class TestCaseForRecipe(BrowserTestCase):
    """Create some sample data for recipe tests."""

    def setUp(self):
        """Provide useful defaults."""
        super(TestCaseForRecipe, self).setUp()
        self.chef = self.factory.makePerson(
            displayname='Master Chef', name='chef', password='test')
        self.user = self.chef
        self.ppa = self.factory.makeArchive(
            displayname='Secret PPA', owner=self.chef, name='ppa')
        self.squirrel = self.factory.makeDistroSeries(
            displayname='Secret Squirrel', name='secret', version='100.04',
            distribution=self.ppa.distribution)
        naked_squirrel = remove_security_proxy_and_shout_at_engineer(
            self.squirrel)
        naked_squirrel.nominatedarchindep = self.squirrel.newArch(
            'i386', ProcessorFamily.get(1), False, self.chef,
            supports_virtualized=True)

    def makeRecipe(self):
        """Create and return a specific recipe."""
        chocolate = self.factory.makeProduct(name='chocolate')
        cake_branch = self.factory.makeProductBranch(
            owner=self.chef, name='cake', product=chocolate)
        return self.factory.makeSourcePackageRecipe(
            owner=self.chef, distroseries=self.squirrel, name=u'cake_recipe',
            description=u'This recipe builds a foo for disto bar, with my'
            ' Secret Squirrel changes.', branches=[cake_branch],
            daily_build_archive=self.ppa)


def get_message_text(browser, index):
    """Return the text of a message, specified by index."""
    tags = find_tags_by_class(browser.contents, 'message')[index]
    return extract_text(tags)


class TestSourcePackageRecipeAddView(TestCaseForRecipe):

    layer = DatabaseFunctionalLayer

    def makeBranch(self):
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        branch = self.factory.makeBranch(
            owner=self.chef, product=product, name='veggies')
        self.factory.makeSourcePackage(sourcepackagename='ratatouille')
        return branch

    def test_create_new_recipe_not_logged_in(self):
        from canonical.launchpad.testing.pages import setupBrowser
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        branch = self.factory.makeBranch(
            owner=self.chef, product=product, name='veggies')
        branch_url = canonical_url(branch)
        logout()

        browser = setupBrowser()
        browser.open(branch_url)

        self.assertRaises(
            Unauthorized, browser.getLink('Create packaging recipe').click)

    def test_create_new_recipe(self):
        branch = self.makeBranch()
        # A new recipe can be created from the branch page.
        browser = self.getUserBrowser(canonical_url(branch), user=self.chef)
        browser.getLink('Create packaging recipe').click()

        browser.getControl(name='field.name').value = 'daily'
        browser.getControl('Description').value = 'Make some food!'
        browser.getControl('Secret Squirrel').click()
        browser.getControl('Build daily').click()
        browser.getControl('Create Recipe').click()

        pattern = """\
            Master Chef's daily recipe
            .*

            Description
            Make some food!

            Recipe information
            Build schedule: Built daily
            Owner: Master Chef
            Base branch: lp://dev/~chef/ratatouille/veggies
            Debian version: 0\+\{revno\}
            Daily build archive: Secret PPA
            Distribution series: Secret Squirrel
            .*

            Recipe contents
            # bzr-builder format 0.2 deb-version 0\+\{revno\}
            lp://dev/~chef/ratatouille/veggies"""
        main_text = extract_text(find_main_content(browser.contents))
        self.assertTextMatchesExpressionIgnoreWhitespace(
            pattern, main_text)

    def test_create_new_recipe_users_teams_as_owner_options(self):
        # Teams that the user is in are options for the recipe owner.
        self.factory.makeTeam(
            name='good-chefs', displayname='Good Chefs', members=[self.chef])
        branch = self.makeBranch()
        browser = self.getUserBrowser(canonical_url(branch), user=self.chef)
        browser.getLink('Create packaging recipe').click()

        # The options for the owner include the Good Chefs team.
        options = browser.getControl('Owner').displayOptions
        self.assertEquals(
            ['Good Chefs (good-chefs)', 'Master Chef (chef)'],
            sorted([str(option) for option in options]))

    def test_create_new_recipe_team_owner(self):
        # New recipes can be owned by teams that the user is a member of.
        team = self.factory.makeTeam(
            name='good-chefs', displayname='Good Chefs', members=[self.chef])
        branch = self.makeBranch()
        browser = self.getUserBrowser(canonical_url(branch), user=self.chef)
        browser.getLink('Create packaging recipe').click()

        browser.getControl(name='field.name').value = 'daily'
        browser.getControl('Description').value = 'Make some food!'
        browser.getControl('Secret Squirrel').click()
        browser.getControl('Build daily').click()
        browser.getControl('Owner').displayValue = ['Good Chefs']
        browser.getControl('Create Recipe').click()

        login(ANONYMOUS)
        recipe = team.getRecipe(u'daily')
        self.assertEqual(team, recipe.owner)
        self.assertEqual('daily', recipe.name)

    def test_create_recipe_forbidden_instruction(self):
        # We don't allow the "run" instruction in our recipes.  Make sure this
        # is communicated to the user properly.
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        branch = self.factory.makeBranch(
            owner=self.chef, product=product, name='veggies')

        # A new recipe can be created from the branch page.
        browser = self.getUserBrowser(canonical_url(branch), user=self.chef)
        browser.getLink('Create packaging recipe').click()

        browser.getControl(name='field.name').value = 'daily'
        browser.getControl('Description').value = 'Make some food!'
        browser.getControl('Secret Squirrel').click()

        browser.getControl('Recipe text').value = (
            browser.getControl('Recipe text').value + 'run cat /etc/passwd')

        browser.getControl('Create Recipe').click()

        self.assertEqual(
            get_message_text(browser, 2),
            'The bzr-builder instruction "run" is not permitted here.')

    def test_create_new_recipe_empty_name(self):
        # Leave off the name and make sure that the widgets validate before
        # the content validates.
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        branch = self.factory.makeBranch(
            owner=self.chef, product=product, name='veggies')

        # A new recipe can be created from the branch page.
        browser = self.getUserBrowser(canonical_url(branch), user=self.chef)
        browser.getLink('Create packaging recipe').click()

        browser.getControl('Description').value = 'Make some food!'
        browser.getControl('Secret Squirrel').click()
        browser.getControl('Create Recipe').click()

        self.assertEqual(
            get_message_text(browser, 2), 'Required input is missing.')

    def createRecipe(self, recipe_text, branch=None):
        if branch is None:
            product = self.factory.makeProduct(
                name='ratatouille', displayname='Ratatouille')
            branch = self.factory.makeBranch(
                owner=self.chef, product=product, name='veggies')

        # A new recipe can be created from the branch page.
        browser = self.getUserBrowser(canonical_url(branch), user=self.chef)
        browser.getLink('Create packaging recipe').click()

        browser.getControl(name='field.name').value = 'daily'
        browser.getControl('Description').value = 'Make some food!'
        browser.getControl('Recipe text').value = recipe_text
        browser.getControl('Create Recipe').click()
        return browser

    def test_create_recipe_bad_text(self):
        # If a user tries to create source package recipe with bad text, they
        # should get an error.
        branch = self.factory.makeBranch(name='veggies')
        package_branch = self.factory.makeBranch(name='packaging')

        browser = self.createRecipe(
            dedent('''
                # bzr-builder format 0.2 deb-version 0+{revno}
                %(branch)s
                merge %(package_branch)s
                ''' % {
                    'branch': branch.bzr_identity,
                    'package_branch': package_branch.bzr_identity,}),
            branch=branch)
        self.assertEqual(
            get_message_text(browser, 2),
            "The recipe text is not a valid bzr-builder recipe. "
            "End of line while looking for '#'")

    def test_create_recipe_no_distroseries(self):
        browser = self.getViewBrowser(self.makeBranch(), '+new-recipe')
        browser.getControl(name='field.name').value = 'daily'
        browser.getControl('Description').value = 'Make some food!'

        browser.getControl('Build daily').click()
        browser.getControl('Create Recipe').click()
        self.assertEqual(
            extract_text(find_tags_by_class(browser.contents, 'message')[2]),
            'You must specify at least one series for daily builds.')

    def test_create_recipe_bad_base_branch(self):
        # If a user tries to create source package recipe with a bad base
        # branch location, they should get an error.
        browser = self.createRecipe(MINIMAL_RECIPE_TEXT % 'foo')
        self.assertEqual(
            get_message_text(browser, 2), 'foo is not a branch on Launchpad.')

    def test_create_recipe_bad_instruction_branch(self):
        # If a user tries to create source package recipe with a bad
        # instruction branch location, they should get an error.
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        branch = self.factory.makeBranch(
            owner=self.chef, product=product, name='veggies')
        recipe = MINIMAL_RECIPE_TEXT % branch.bzr_identity
        recipe += 'nest packaging foo debian'
        browser = self.createRecipe(recipe, branch)
        self.assertEqual(
            get_message_text(browser, 2), 'foo is not a branch on Launchpad.')

    def test_create_dupe_recipe(self):
        # You shouldn't be able to create a duplicate recipe owned by the same
        # person with the same name.
        recipe = self.factory.makeSourcePackageRecipe(owner=self.chef)
        transaction.commit()
        recipe_name = recipe.name

        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        branch = self.factory.makeBranch(
            owner=self.chef, product=product, name='veggies')

        # A new recipe can be created from the branch page.
        browser = self.getUserBrowser(canonical_url(branch), user=self.chef)
        browser.getLink('Create packaging recipe').click()

        browser.getControl(name='field.name').value = recipe_name
        browser.getControl('Description').value = 'Make some food!'
        browser.getControl('Secret Squirrel').click()
        browser.getControl('Create Recipe').click()

        self.assertEqual(
            get_message_text(browser, 2),
            'There is already a recipe owned by Master Chef with this name.')

    def test_create_recipe_private_branch(self):
        # If a user tries to create source package recipe with a private
        # base branch, they should get an error.
        branch = self.factory.makeAnyBranch(private=True, owner=self.user)
        with person_logged_in(self.user):
            bzr_identity = branch.bzr_identity
        recipe_text = MINIMAL_RECIPE_TEXT % bzr_identity
        browser = self.createRecipe(recipe_text)
        self.assertEqual(
            get_message_text(browser, 2),
            'Recipe may not refer to private branch: %s' % bzr_identity)


class TestSourcePackageRecipeEditView(TestCaseForRecipe):
    """Test the editing behaviour of a source package recipe."""

    layer = DatabaseFunctionalLayer

    def test_edit_recipe(self):
        self.factory.makeDistroSeries(
            displayname='Mumbly Midget', name='mumbly',
            distribution=self.ppa.distribution)
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        veggie_branch = self.factory.makeBranch(
            owner=self.chef, product=product, name='veggies')
        meat_branch = self.factory.makeBranch(
            owner=self.chef, product=product, name='meat')
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, registrant=self.chef,
            name=u'things', description=u'This is a recipe',
            distroseries=self.squirrel, branches=[veggie_branch],
            daily_build_archive=self.ppa)
        self.factory.makeArchive(
            distribution=self.ppa.distribution, name='ppa2',
            displayname="PPA 2", owner=self.chef)

        meat_path = meat_branch.bzr_identity

        browser = self.getUserBrowser(canonical_url(recipe), user=self.chef)
        browser.getLink('Edit recipe').click()
        browser.getControl(name='field.name').value = 'fings'
        browser.getControl('Description').value = 'This is stuff'
        browser.getControl('Recipe text').value = (
            MINIMAL_RECIPE_TEXT % meat_path)
        browser.getControl('Secret Squirrel').click()
        browser.getControl('Mumbly Midget').click()
        browser.getControl('PPA 2').click()
        browser.getControl('Update Recipe').click()

        pattern = """\
            Master Chef's fings recipe
            .*

            Description
            This is stuff

            Recipe information
            Build schedule: Built on request
            Owner: Master Chef
            Base branch: lp://dev/~chef/ratatouille/meat
            Debian version: 0\+\{revno\}
            Daily build archive:
            PPA 2
            Distribution series: Mumbly Midget
            .*

            Recipe contents
            # bzr-builder format 0.2 deb-version 0\+\{revno\}
            lp://dev/~chef/ratatouille/meat"""
        main_text = extract_text(find_main_content(browser.contents))
        self.assertTextMatchesExpressionIgnoreWhitespace(
            pattern, main_text)

    def test_edit_recipe_forbidden_instruction(self):
        self.factory.makeDistroSeries(
            displayname='Mumbly Midget', name='mumbly',
            distribution=self.ppa.distribution)
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        veggie_branch = self.factory.makeBranch(
            owner=self.chef, product=product, name='veggies')
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
            extract_text(find_tags_by_class(browser.contents, 'message')[1]),
            'The bzr-builder instruction "run" is not permitted here.')

    def test_edit_recipe_already_exists(self):
        self.factory.makeDistroSeries(
            displayname='Mumbly Midget', name='mumbly',
            distribution=self.ppa.distribution)
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        veggie_branch = self.factory.makeBranch(
            owner=self.chef, product=product, name='veggies')
        meat_branch = self.factory.makeBranch(
            owner=self.chef, product=product, name='meat')
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, registrant=self.chef,
            name=u'things', description=u'This is a recipe',
            distroseries=self.squirrel, branches=[veggie_branch])
        self.factory.makeSourcePackageRecipe(
            owner=self.chef, registrant=self.chef,
            name=u'fings', description=u'This is a recipe',
            distroseries=self.squirrel, branches=[veggie_branch])

        meat_path = meat_branch.bzr_identity

        browser = self.getUserBrowser(canonical_url(recipe), user=self.chef)
        browser.getLink('Edit recipe').click()
        browser.getControl(name='field.name').value = 'fings'
        browser.getControl('Description').value = 'This is stuff'
        browser.getControl('Recipe text').value = (
            MINIMAL_RECIPE_TEXT % meat_path)
        browser.getControl('Secret Squirrel').click()
        browser.getControl('Mumbly Midget').click()
        browser.getControl('Update Recipe').click()

        self.assertEqual(
            extract_text(find_tags_by_class(browser.contents, 'message')[1]),
            'There is already a recipe owned by Master Chef with this name.')

    def test_edit_recipe_but_not_name(self):
        self.factory.makeDistroSeries(
            displayname='Mumbly Midget', name='mumbly',
            distribution=self.ppa.distribution)
        product = self.factory.makeProduct(
            name='ratatouille', displayname='Ratatouille')
        veggie_branch = self.factory.makeBranch(
            owner=self.chef, product=product, name='veggies')
        meat_branch = self.factory.makeBranch(
            owner=self.chef, product=product, name='meat')
        ppa = self.factory.makeArchive(name='ppa')
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, registrant=self.chef,
            name=u'things', description=u'This is a recipe',
            distroseries=self.squirrel, branches=[veggie_branch],
            daily_build_archive=ppa)

        meat_path = meat_branch.bzr_identity

        browser = self.getUserBrowser(canonical_url(recipe), user=self.chef)
        browser.getLink('Edit recipe').click()
        browser.getControl('Description').value = 'This is stuff'
        browser.getControl('Recipe text').value = (
            MINIMAL_RECIPE_TEXT % meat_path)
        browser.getControl('Secret Squirrel').click()
        browser.getControl('Mumbly Midget').click()
        browser.getControl('Update Recipe').click()

        pattern = """\
            Master Chef's things recipe
            .*

            Description
            This is stuff

            Recipe information
            Build schedule: Built on request
            Owner: Master Chef
            Base branch: lp://dev/~chef/ratatouille/meat
            Debian version: 0\+\{revno\}
            Daily build archive:
            Secret PPA
            Distribution series: Mumbly Midget
            .*

            Recipe contents
            # bzr-builder format 0.2 deb-version 0\+\{revno\}
            lp://dev/~chef/ratatouille/meat"""
        main_text = extract_text(find_main_content(browser.contents))
        self.assertTextMatchesExpressionIgnoreWhitespace(
            pattern, main_text)

    def test_edit_recipe_private_branch(self):
        # If a user tries to set source package recipe to use a private
        # branch, they should get an error.
        recipe = self.factory.makeSourcePackageRecipe(owner=self.user)
        branch = self.factory.makeAnyBranch(private=True, owner=self.user)
        with person_logged_in(self.user):
            bzr_identity = branch.bzr_identity
        recipe_text = MINIMAL_RECIPE_TEXT % bzr_identity
        browser = self.getViewBrowser(recipe, '+edit')
        browser.getControl('Recipe text').value = recipe_text
        browser.getControl('Update Recipe').click()
        self.assertEqual(
            get_message_text(browser, 1),
            'Recipe may not refer to private branch: %s' % bzr_identity)


class TestSourcePackageRecipeView(TestCaseForRecipe):

    layer = DatabaseFunctionalLayer

    def test_index(self):
        recipe = self.makeRecipe()
        build = removeSecurityProxy(self.factory.makeSourcePackageRecipeBuild(
            recipe=recipe, distroseries=self.squirrel, archive=self.ppa))
        build.buildstate = BuildStatus.FULLYBUILT
        build.datebuilt = datetime(2010, 03, 16, tzinfo=utc)

        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Master Chef Recipes cake_recipe
            .*
            Description
            This recipe .*changes.

            Recipe information
            Build schedule: Built on request
            Owner: Master Chef
            Base branch: lp://dev/~chef/chocolate/cake
            Debian version: 0\+\{revno\}
            Daily build archive: Secret PPA
            Distribution series: Secret Squirrel

            Build records
            Status Time Distribution series Archive
            Successful build on 2010-03-16 Secret Squirrel Secret PPA
            Request build\(s\)

            Recipe contents
            # bzr-builder format 0.2 deb-version 0\+\{revno\}
            lp://dev/~chef/chocolate/cake""", self.getMainText(recipe))

    def test_index_no_builds(self):
        """A message should be shown when there are no builds."""
        recipe = self.makeRecipe()
        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Build records
            Status Time Distribution series Archive
            This recipe has not been built yet.""", self.getMainText(recipe))

    def test_index_no_suitable_builders(self):
        recipe = self.makeRecipe()
        removeSecurityProxy(self.factory.makeSourcePackageRecipeBuild(
            recipe=recipe, distroseries=self.squirrel, archive=self.ppa))
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            Build records
            Status Time Distribution series Archive
            No suitable builders Secret Squirrel Secret PPA
            Request build\(s\)""", self.getMainText(recipe))

    def makeBuildJob(self, recipe):
        """Return a build associated with a buildjob."""
        build = self.factory.makeSourcePackageRecipeBuild(
            recipe=recipe, distroseries=self.squirrel, archive=self.ppa)
        self.factory.makeSourcePackageRecipeBuildJob(recipe_build=build)
        return build

    def test_index_pending(self):
        """Test the listing of a pending build."""
        recipe = self.makeRecipe()
        self.makeBuildJob(recipe)
        self.factory.makeBuilder()
        pattern = """\
            Build records
            Status Time Distribution series Archive
            Pending build in .* \(estimated\) Secret Squirrel Secret PPA
            Request build\(s\)

            Recipe contents"""
        main_text = self.getMainText(recipe)
        self.assertTextMatchesExpressionIgnoreWhitespace(
            pattern, main_text)

    def test_builds(self):
        """Ensure SourcePackageRecipeView.builds is as described."""
        recipe = self.makeRecipe()
        build1 = self.makeBuildJob(recipe=recipe)
        build2 = self.makeBuildJob(recipe=recipe)
        build3 = self.makeBuildJob(recipe=recipe)
        build4 = self.makeBuildJob(recipe=recipe)
        build5 = self.makeBuildJob(recipe=recipe)
        build6 = self.makeBuildJob(recipe=recipe)
        view = SourcePackageRecipeView(recipe, None)
        self.assertEqual(
            set([build1, build2, build3, build4, build5, build6]),
            set(view.builds))

        def set_day(build, day):
            removeSecurityProxy(build).datebuilt = datetime(
                2010, 03, day, tzinfo=utc)
        set_day(build1, 16)
        set_day(build2, 15)
        # When there are 4+ pending builds, only the the most
        # recently-completed build is returned (i.e. build1, not build2)
        self.assertEqual(
            set([build1, build3, build4, build5, build6]),
            set(view.builds))
        set_day(build3, 14)
        set_day(build4, 13)
        set_day(build5, 12)
        set_day(build6, 11)
        self.assertEqual(
            [build1, build2, build3, build4, build5], view.builds)

    def test_request_builds_page(self):
        """Ensure the +request-builds page is sane."""
        recipe = self.makeRecipe()
        pattern = dedent("""\
            Request builds for cake_recipe
            Master Chef
            Recipes
            cake_recipe
            Request builds for cake_recipe
            Archive:
            Secret PPA (chef/ppa)
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
        woody = self.factory.makeDistroSeries(
            name='woody', displayname='Woody',
            distribution=self.ppa.distribution)
        naked_woody = remove_security_proxy_and_shout_at_engineer(woody)
        naked_woody.nominatedarchindep = woody.newArch(
            'i386', ProcessorFamily.get(1), False, self.factory.makePerson(),
            supports_virtualized=True)

        recipe = self.makeRecipe()
        browser = self.getViewBrowser(recipe, '+request-builds')
        browser.getControl('Woody').click()
        browser.getControl('Request builds').click()

        login(ANONYMOUS)
        builds = recipe.getBuilds(True)
        build_distros = [
            build.distroseries.displayname for build in builds]
        build_distros.sort()
        # Secret Squirrel is checked by default.
        self.assertEqual(['Secret Squirrel', 'Woody'], build_distros)
        self.assertEqual(
            set([2505]),
            set(build.buildqueue_record.lastscore for build in builds))

    def test_request_builds_archive(self):
        recipe = self.factory.makeSourcePackageRecipe()
        ppa2 = self.factory.makeArchive(
            displayname='Secret PPA', owner=self.chef, name='ppa2')
        view = SourcePackageRecipeRequestBuildsView(recipe, None)
        self.assertIs(None, view.initial_values.get('archive'))
        self.factory.makeSourcePackageRecipeBuild(recipe=recipe, archive=ppa2)
        self.assertEqual(ppa2, view.initial_values.get('archive'))

    def test_request_build_rejects_over_quota(self):
        """Over-quota build requests cause validation failures."""
        woody = self.factory.makeDistroSeries(
            name='woody', displayname='Woody',
            distribution=self.ppa.distribution)
        naked_woody = remove_security_proxy_and_shout_at_engineer(woody)
        naked_woody.nominatedarchindep = woody.newArch(
            'i386', ProcessorFamily.get(1), False, self.factory.makePerson(),
            supports_virtualized=True)

        recipe = self.makeRecipe()
        for x in range(5):
            build = recipe.requestBuild(
                self.ppa, self.chef, woody, PackagePublishingPocket.RELEASE)
            removeSecurityProxy(build).buildstate = BuildStatus.FULLYBUILT

        browser = self.getViewBrowser(recipe, '+request-builds')
        browser.getControl('Woody').click()
        browser.getControl('Request builds').click()
        self.assertIn("You have exceeded today's quota for ubuntu woody.",
                extract_text(find_main_content(browser.contents)))

    def test_request_builds_rejects_duplicate(self):
        """Over-quota build requests cause validation failures."""
        woody = self.factory.makeDistroSeries(
            name='woody', displayname='Woody',
            distribution=self.ppa.distribution)
        naked_woody = remove_security_proxy_and_shout_at_engineer(woody)
        naked_woody.nominatedarchindep = woody.newArch(
            'i386', ProcessorFamily.get(1), False, self.factory.makePerson(),
            supports_virtualized=True)

        recipe = self.makeRecipe()
        recipe.requestBuild(
            self.ppa, self.chef, woody, PackagePublishingPocket.RELEASE)

        browser = self.getViewBrowser(recipe, '+request-builds')
        browser.getControl('Woody').click()
        browser.getControl('Request builds').click()
        self.assertIn(
            "An identical build is already pending for ubuntu woody.",
            extract_text(find_main_content(browser.contents)))


class TestSourcePackageRecipeBuildView(BrowserTestCase):
    """Test behaviour of SourcePackageReciptBuildView."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        """Provide useful defaults."""
        super(TestSourcePackageRecipeBuildView, self).setUp()
        self.user = self.factory.makePerson(
            displayname='Owner', name='build-owner', password='test')

    def makeBuild(self, buildstate=None):
        """Make a build suitabe for testing."""
        archive = self.factory.makeArchive(name='build',
            owner=self.user)
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.user, name=u'my-recipe')
        distro_series = self.factory.makeDistroSeries(
            name='squirrel', distribution=archive.distribution)
        build = self.factory.makeSourcePackageRecipeBuild(
            requester=self.user, archive=archive, recipe=recipe,
            distroseries=distro_series)
        self.factory.makeSourcePackageRecipeBuildJob(recipe_build=build)
        self.factory.makeBuilder()
        return build

    def makeBuildView(self):
        """Return a view of a build suitable for testing."""
        return SourcePackageRecipeBuildView(self.makeBuild(), None)

    def test_estimate(self):
        """Time should be estimated until the job is completed."""
        view = self.makeBuildView()
        self.assertTrue(view.estimate)
        view.context.buildqueue_record.job.start()
        self.assertTrue(view.estimate)
        removeSecurityProxy(view.context).datebuilt = datetime.now(utc)
        self.assertFalse(view.estimate)

    def test_eta(self):
        """ETA should be reasonable.

        It should be None if there is no builder or queue entry.
        It should be getEstimatedJobStartTime + estimated duration for jobs
        that have not started.
        It should be job.date_started + estimated duration for jobs that have
        started.
        """
        build = self.factory.makeSourcePackageRecipeBuild()
        view = SourcePackageRecipeBuildView(build, None)
        self.assertIs(None, view.eta)
        queue_entry = self.factory.makeSourcePackageRecipeBuildJob(
            recipe_build=build)
        queue_entry._now = lambda: datetime(1970, 1, 1, 0, 0, 0, 0, utc)
        self.factory.makeBuilder()
        self.assertIsNot(None, view.eta)
        self.assertEqual(
            queue_entry.getEstimatedJobStartTime() +
            queue_entry.estimated_duration, view.eta)
        queue_entry.job.start()
        self.assertEqual(
            queue_entry.job.date_started + queue_entry.estimated_duration,
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
            Code
            my-recipe
            created .*
            Build status
            Needs building
            Start in .* \\(9876\\) What's this?.*
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
        naked_build = removeSecurityProxy(release.source_package_recipe_build)
        naked_build.buildstate = BuildStatus.FULLYBUILT
        naked_build.buildduration = timedelta(minutes=1)
        naked_build.datebuilt = datetime(2009, 1, 1, tzinfo=utc)
        naked_build.buildqueue_record.destroySelf()
        naked_build.buildlog = self.factory.makeLibraryFileAlias(
            content='buildlog')
        naked_build.upload_log = self.factory.makeLibraryFileAlias(
            content='upload_log')
        main_text = self.getMainText(
            release.source_package_recipe_build, '+index')
        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Code
            my-recipe
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
            processorfamily=self.factory.makeProcessorFamily())
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
        removeSecurityProxy(build).buildstate = BuildStatus.BUILDING
        main_text = self.getMainText(build, '+index')
        self.assertIn('Logs have no tails!', main_text)
        removeSecurityProxy(build).buildstate = BuildStatus.FULLYBUILT
        self.assertIn('Logs have no tails!', main_text)

    def getMainText(self, build, view_name=None):
        """"Return the main text of a view's web page."""
        browser = self.getViewBrowser(build, '+index')
        return extract_text(find_main_content(browser.contents))

    def test_buildlog(self):
        """A link to the build log is shown if available."""
        build = self.makeBuild()
        removeSecurityProxy(build).buildlog = (
            self.factory.makeLibraryFileAlias())
        build_log_url = build.build_log_url
        browser = self.getViewBrowser(build)
        link = browser.getLink('buildlog')
        self.assertEqual(build_log_url, link.url)

    def test_uploadlog(self):
        """A link to the upload log is shown if available."""
        build = self.makeBuild()
        removeSecurityProxy(build).upload_log = (
            self.factory.makeLibraryFileAlias())
        upload_log_url = build.upload_log_url
        browser = self.getViewBrowser(build)
        link = browser.getLink('uploadlog')
        self.assertEqual(upload_log_url, link.url)


class TestSourcePackageRecipeDeleteView(TestCaseForRecipe):

    layer = DatabaseFunctionalLayer

    def test_delete_recipe(self):
        recipe = self.factory.makeSourcePackageRecipe(owner=self.chef)

        browser = self.getUserBrowser(
            canonical_url(recipe), user=self.chef)

        browser.getLink('Delete recipe').click()
        browser.getControl('Delete recipe').click()

        self.assertEqual(
            'http://code.launchpad.dev/~chef',
            browser.url)
