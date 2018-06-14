# Copyright 2010-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for product views."""

__metaclass__ = type

__all__ = ['make_product_form']

import re
from urlparse import urlsplit

from lazr.restful.interfaces import IJSONRequestCache
from soupmatchers import (
    HTMLContains,
    Tag,
    )
from testtools.matchers import (
    LessThan,
    MatchesAll,
    Not,
    )
import transaction
from zope.component import getUtility
from zope.schema.vocabulary import SimpleVocabulary
from zope.security.proxy import removeSecurityProxy

from lp.app.browser.lazrjs import vocabulary_to_choice_edit_items
from lp.app.enums import (
    InformationType,
    ServiceUsage,
    )
from lp.code.enums import RevisionControlSystems
from lp.code.interfaces.codeimport import CODE_IMPORT_GIT_TARGET_FEATURE_FLAG
from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.code.tests.helpers import GitHostingFixture
from lp.registry.browser.product import (
    ProjectAddStepOne,
    ProjectAddStepTwo,
    )
from lp.registry.enums import (
    EXCLUSIVE_TEAM_POLICY,
    TeamMembershipPolicy,
    VCSType,
    )
from lp.registry.interfaces.product import (
    IProductSet,
    License,
    )
from lp.registry.model.product import Product
from lp.services.config import config
from lp.services.database.interfaces import IStore
from lp.services.features.testing import FeatureFixture
from lp.services.webapp.publisher import canonical_url
from lp.services.webapp.vhosts import allvhosts
from lp.testing import (
    BrowserTestCase,
    login_celebrity,
    login_person,
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.fixture import DemoMode
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.matchers import HasQueryCount
from lp.testing.pages import find_tag_by_id
from lp.testing.service_usage_helpers import set_service_usage
from lp.testing.views import (
    create_initialized_view,
    create_view,
    )


class TestProductConfiguration(BrowserTestCase):
    """Tests the configuration links and helpers."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductConfiguration, self).setUp()
        self.product = self.factory.makeProduct()

    def test_registration_not_done(self):
        # The registration done property on the product index view
        # tells you if all the configuration work is done, based on
        # usage enums.

        # At least one usage enum is unknown, so registration done is false.
        self.assertEqual(
            self.product.codehosting_usage,
            ServiceUsage.UNKNOWN)
        view = create_view(self.product, '+get-involved')
        self.assertFalse(view.registration_done)

        set_service_usage(
            self.product.name,
            codehosting_usage="EXTERNAL",
            bug_tracking_usage="LAUNCHPAD",
            answers_usage="EXTERNAL",
            translations_usage="NOT_APPLICABLE")
        view = create_view(self.product, '+get-involved')
        self.assertTrue(view.registration_done)

    lp_tag = Tag('lp_tag', 'input', attrs={'value': 'LAUNCHPAD'})

    def test_configure_answers_has_launchpad_for_public(self):
        # Public projects support LAUNCHPAD for answers.
        browser = self.getViewBrowser(self.product, '+configure-answers',
            user=self.product.owner)
        self.assertThat(browser.contents, HTMLContains(self.lp_tag))

    def test_configure_answers_skips_launchpad_for_proprietary(self):
        # Proprietary projects forbid LAUNCHPAD for answers.
        product = self.factory.makeProduct(
            information_type=InformationType.PROPRIETARY)
        with person_logged_in(None):
            browser = self.getViewBrowser(product, '+configure-answers',
                user=removeSecurityProxy(product).owner)
        self.assertThat(browser.contents, Not(HTMLContains(self.lp_tag)))


def make_product_form(person=None, action=1, proprietary=False):
    """Return form data for product creation.

    :param person: A person to associate with the product.  Mandatory for
        proprietary.
    :param action: 1 means submit step 1.  2 means submit step 2 (completion)
    :param proprietary: If true, create a PROPRIETARY product.
    """
    if action == 1:
        return {
            'field.actions.continue': 'Continue',
            'field.__visited_steps__': ProjectAddStepOne.step_name,
            'field.display_name': 'Fnord',
            'field.name': 'fnord',
            'field.summary': 'fnord summary',
            }
    else:
        form = {
            'field.actions.continue': 'Continue',
            'field.__visited_steps__': '%s|%s' % (
                ProjectAddStepOne.step_name, ProjectAddStepTwo.step_name),
            'field.display_name': 'Fnord',
            'field.name': 'fnord',
            'field.summary': 'fnord summary',
            'field.disclaim_maintainer': 'off',
            }
        if proprietary:
            form['field.information_type'] = 'PROPRIETARY'
            form['field.owner'] = person.name
            form['field.driver'] = person.name
            form['field.bug_supervisor'] = person.name
            form['field.licenses'] = License.OTHER_PROPRIETARY.title
            form['field.license_info'] = 'Commercial Subscription'
        else:
            form['field.information_type'] = 'PUBLIC'
            form['field.owner'] = ''
            form['field.licenses'] = ['MIT']
            form['field.license_info'] = ''
        return form


class TestProductAddView(TestCaseWithFactory):
    """Tests the configuration links and helpers."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductAddView, self).setUp()
        self.product_set = getUtility(IProductSet)

    def test_view_data_model(self):
        # The view's json request cache contains the expected data.
        view = create_initialized_view(self.product_set, '+new')
        cache = IJSONRequestCache(view.request)
        policy_items = [(item.name, item) for item in EXCLUSIVE_TEAM_POLICY]
        team_membership_policy_data = vocabulary_to_choice_edit_items(
            SimpleVocabulary.fromItems(policy_items),
            value_fn=lambda item: item.name)
        self.assertContentEqual(
            team_membership_policy_data,
            cache.objects['team_membership_policy_data'])

    def test_staging_message_is_not_demo(self):
        view = create_initialized_view(self.product_set, '+new')
        message = find_tag_by_id(view.render(), 'staging-message')
        self.assertTrue(message is not None)

    def test_staging_message_is_demo(self):
        config.push(self.id(), '')
        self.addCleanup(config.pop, self.id())
        self.useFixture(DemoMode())
        view = create_initialized_view(self.product_set, '+new')
        message = find_tag_by_id(view.render(), 'staging-message')
        self.assertEqual(None, message)

    def test_step_two_initialize(self):
        # Step two collects additional license, owner, and packaging info.
        registrant = self.factory.makePerson(name='pting')
        transaction.commit()
        login_person(registrant)
        form = make_product_form(action=1)
        view = create_initialized_view(self.product_set, '+new', form=form)
        owner_widget = view.view.widgets['owner']
        self.assertEqual('pting', view.view.initial_values['owner'])
        self.assertEqual('Select the maintainer', owner_widget.header)
        self.assertIs(True, owner_widget.show_create_team_link)
        disclaim_widget = view.view.widgets['disclaim_maintainer']
        self.assertEqual('subordinate', disclaim_widget.cssClass)
        self.assertEqual(
            ['display_name', 'name', 'summary', 'description',
             'homepageurl', 'information_type', 'licenses', 'license_info',
             'driver', 'bug_supervisor', 'owner',
             '__visited_steps__'],
            view.view.field_names)
        self.assertEqual(
            ['display_name', 'name', 'summary', 'description',
             'homepageurl', 'information_type', 'licenses', 'driver',
             'bug_supervisor', 'owner', 'disclaim_maintainer',
             'source_package_name', 'distroseries', '__visited_steps__',
             'license_info'],
            [f.__name__ for f in view.view.form_fields])

    def test_owner_can_be_team(self):
        # An owner can be any valid user or team selected.
        registrant = self.factory.makePerson()
        team = self.factory.makeTeam(
            membership_policy=TeamMembershipPolicy.RESTRICTED)
        transaction.commit()
        login_person(registrant)
        form = make_product_form(action=2)
        form['field.owner'] = team.name
        view = create_initialized_view(self.product_set, '+new', form=form)
        self.assertEqual(0, len(view.view.errors))
        product = self.product_set.getByName('fnord')
        self.assertEqual(team, product.owner)

    def test_disclaim_maitainer_supersedes_owner(self):
        # When the disclaim_maintainer is selected, the owner field is ignored
        # and the registry team is made the maintainer.
        registrant = self.factory.makePerson()
        login_person(registrant)
        form = make_product_form(action=2)
        form['field.owner'] = registrant.name
        form['field.disclaim_maintainer'] = 'on'
        view = create_initialized_view(self.product_set, '+new', form=form)
        self.assertEqual(0, len(view.view.errors))
        product = self.product_set.getByName('fnord')
        self.assertEqual('registry', product.owner.name)

    def test_owner_is_requried_without_disclaim_maintainer(self):
        # A valid owner name is required if disclaim_maintainer is
        # not selected.
        registrant = self.factory.makePerson()
        login_person(registrant)
        form = make_product_form(action=2)
        form['field.owner'] = ''
        del form['field.disclaim_maintainer']
        view = create_initialized_view(self.product_set, '+new', form=form)
        self.assertEqual(1, len(view.view.errors))
        self.assertEqual('owner', view.view.errors[0][0])

    def test_disclaim_maitainer_empty_supersedes_owner(self):
        # Errors for the owner field are ignored when disclaim_maintainer is
        # selected.
        registrant = self.factory.makePerson()
        login_person(registrant)
        form = make_product_form(action=2)
        form['field.owner'] = ''
        form['field.disclaim_maintainer'] = 'on'
        form['field.information_type'] = 'PUBLIC'
        view = create_initialized_view(self.product_set, '+new', form=form)
        self.assertEqual(0, len(view.view.errors))
        product = self.product_set.getByName('fnord')
        self.assertEqual('registry', product.owner.name)

    def test_information_type_saved_new_product_updated(self):
        # information_type will be updated if passed in via form data,
        # if the private projects feature flag is enabled.
        registrant = self.factory.makePerson()
        login_person(registrant)
        form = make_product_form(registrant, action=2, proprietary=True)
        form['field.maintainer'] = registrant.name
        view = create_initialized_view(
            self.product_set, '+new', form=form)
        self.assertEqual(0, len(view.view.errors))
        product = self.product_set.getByName('fnord')
        self.assertEqual(
            InformationType.PROPRIETARY, product.information_type)


class TestProductView(BrowserTestCase):
    """Tests the ProductView."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductView, self).setUp()
        self.product = self.factory.makeProduct(name='fnord')

    def test_code_link_bzr(self):
        branch = self.factory.makeBranch(target=self.product)
        # No browse link unless there are revisions.
        self.factory.makeRevisionsForBranch(branch)
        with person_logged_in(self.product.owner):
            self.product.development_focus.branch = branch
            self.product.vcs = VCSType.BZR
        view = create_initialized_view(self.product, "+index")
        html = view()
        self.assertThat(
            html,
            MatchesAll(
                HTMLContains(
                    Tag("branch link", "a",
                        text="lp://dev/%s" % self.product.name,
                        attrs={"href": canonical_url(branch)})),
                HTMLContains(
                    Tag("code browser link", "a", text="Browse the code",
                        attrs={"href": branch.getCodebrowseUrl('files')}))))

    def test_code_link_git(self):
        repo = self.factory.makeGitRepository(target=self.product)
        with person_logged_in(repo.target.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                target=self.product, repository=repo)
            self.product.vcs = VCSType.GIT
        view = create_initialized_view(self.product, "+index")
        html = view()
        self.assertThat(
            html,
            MatchesAll(
                HTMLContains(
                    Tag("repo link", "a",
                        text="lp:%s" % self.product.name,
                        attrs={"href": canonical_url(repo)})),
                HTMLContains(
                    Tag("code browser link", "a", text="Browse the code",
                        attrs={"href": repo.getCodebrowseUrl()}))))

    def test_golang_meta_renders_git(self):
        # ensure golang meta import path is rendered if project has
        # git default vcs.
        # See: https://golang.org/cmd/go/#hdr-Remote_import_paths
        repo = self.factory.makeGitRepository()
        view = create_initialized_view(repo.target, '+index')
        with person_logged_in(repo.target.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                target=repo.target, repository=repo)
            repo.target.vcs = VCSType.GIT

        golang_import = '{base}/{product_name} git {repo_url}'.format(
            base=config.vhost.mainsite.hostname,
            product_name=repo.target.name,
            repo_url=repo.git_https_url
            )
        self.assertEqual(golang_import, view.golang_import_spec)
        meta_tag = Tag('go-import-meta', 'meta',
                       attrs={'name': 'go-import', 'content': golang_import})
        browser = self.getViewBrowser(repo.target, '+index',
                                      user=repo.target.owner)
        self.assertThat(browser.contents, HTMLContains(meta_tag))

    def test_golang_meta_renders_bzr(self):
        # ensure golang meta import path is rendered if project has
        # bzr default vcs.
        # See: https://golang.org/cmd/go/#hdr-Remote_import_paths
        owner = self.factory.makePerson(name='zardoz')
        product = self.factory.makeProduct(name='wapcaplet')
        branch = self.factory.makeBranch(product=product, name='a-branch',
                                         owner=owner)
        view = create_initialized_view(branch.product, '+index')

        with person_logged_in(branch.product.owner):
            branch.product.development_focus.branch = branch
            branch.product.vcs = VCSType.BZR

        golang_import = (
            "{hostname}/wapcaplet bzr "
            "{root_url}~zardoz/wapcaplet/a-branch").format(
                hostname=config.vhost.mainsite.hostname,
                root_url=allvhosts.configs['mainsite'].rooturl)
        self.assertEqual(golang_import, view.golang_import_spec)
        meta_tag = Tag('go-import-meta', 'meta',
                       attrs={'name': 'go-import', 'content': golang_import})
        browser = self.getViewBrowser(branch.product, '+index',
                                      user=branch.owner)
        self.assertThat(browser.contents, HTMLContains(meta_tag))

    def test_golang_meta_no_default_vcs(self):
        # ensure golang meta import path is not rendered without
        # a default vcs
        branch = self.factory.makeBranch()
        view = create_initialized_view(branch.product, '+index')
        self.assertIsNone(view.golang_import_spec)

    def test_golang_meta_no_default_branch(self):
        # ensure golang meta import path is not rendered without
        # a product development_focus.
        branch = self.factory.makeBranch()
        view = create_initialized_view(branch.product, '+index')
        with person_logged_in(branch.product.owner):
            branch.product.vcs = VCSType.BZR
        self.assertIsNone(view.golang_import_spec)

    def test_golang_meta_no_default_repo(self):
        # ensure golang meta import path is not rendered without
        # a default repo.
        repo = self.factory.makeGitRepository()
        view = create_initialized_view(repo.target, '+index')
        with person_logged_in(repo.target.owner):
            repo.target.vcs = VCSType.GIT
        self.assertIsNone(view.golang_import_spec)

    def test_golang_meta_no_permissions(self):
        # ensure golang meta import path is not rendered if user does
        # not have launchpad.View permissions on branch.
        simple_user = self.factory.makePerson()
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        branch = self.factory.makeBranch(
            owner=owner, information_type=InformationType.PRIVATESECURITY)

        with person_logged_in(owner):
            product.development_focus.branch = branch
            product.vcs = VCSType.BZR
            view = create_initialized_view(product, '+index')
            self.assertIsNot(None, view.golang_import_spec)

        with person_logged_in(simple_user):
            view = create_initialized_view(product, '+index')
            self.assertIsNone(view.golang_import_spec)

    def test_show_programming_languages_without_languages(self):
        # show_programming_languages is false when there are no programming
        # languages set.
        view = create_initialized_view(self.product, '+index')
        self.assertEqual(None, self.product.programminglang)
        self.assertFalse(view.show_programming_languages)

    def test_show_programming_languages_with_languages(self):
        # show_programming_languages is true when programming languages
        # are set.
        with person_logged_in(self.product.owner):
            self.product.programminglang = 'C++'
        view = create_initialized_view(self.product, '+index')
        self.assertTrue(view.show_programming_languages)

    def test_show_inferred_vcs(self):
        with person_logged_in(self.product.owner):
            self.product.vcs = VCSType.GIT
        browser = self.getViewBrowser(self.product, '+index')
        self.assertIn(VCSType.GIT.title, browser.contents)

    def test_show_license_info_without_other_license(self):
        # show_license_info is false when one of the "other" licences is
        # not selected.
        view = create_initialized_view(self.product, '+index')
        self.assertEqual((License.GNU_GPL_V2, ), self.product.licenses)
        self.assertFalse(view.show_license_info)

    def test_show_license_info_with_other_open_source_license(self):
        # show_license_info is true when the Other/Open Source licence is
        # selected.
        view = create_initialized_view(self.product, '+index')
        with person_logged_in(self.product.owner):
            self.product.licenses = [License.OTHER_OPEN_SOURCE]
        self.assertTrue(view.show_license_info)

    def test_show_license_info_with_other_open_proprietary_license(self):
        # show_license_info is true when the Other/Proprietary licence is
        # selected.
        view = create_initialized_view(self.product, '+index')
        with person_logged_in(self.product.owner):
            self.product.licenses = [License.OTHER_PROPRIETARY]
        self.assertTrue(view.show_license_info)

    def test_is_proprietary_with_proprietary_license(self):
        # is_proprietary is true when the project has a proprietary licence.
        with person_logged_in(self.product.owner):
            self.product.licenses = [License.OTHER_PROPRIETARY]
        view = create_initialized_view(self.product, '+index')
        self.assertTrue(view.is_proprietary)

    def test_is_proprietary_without_proprietary_license(self):
        # is_proprietary is false when the project has a proprietary licence.
        with person_logged_in(self.product.owner):
            self.product.licenses = [License.GNU_GPL_V2]
        view = create_initialized_view(self.product, '+index')
        self.assertFalse(view.is_proprietary)

    def test_active_widget(self):
        # The active widget is is unique to the product.
        view = create_initialized_view(self.product, '+index')
        widget = view.active_widget
        self.assertEqual('fnord-edit-active', widget.content_box_id)
        self.assertEqual(
            canonical_url(self.product, view_name='+review-license'),
            widget.edit_url)

    def test_project_reviewed_widget(self):
        # The licence reviewed widget is is unique to the product.
        login_celebrity('registry_experts')
        view = create_initialized_view(self.product, '+index')
        widget = view.project_reviewed_widget
        self.assertEqual('fnord-edit-project-reviewed', widget.content_box_id)
        self.assertEqual(
            canonical_url(self.product, view_name='+review-license'),
            widget.edit_url)

    def test_license_approved_widget_any_license(self):
        # The licence approved widget is is unique to the product.
        login_celebrity('registry_experts')
        view = create_initialized_view(self.product, '+index')
        widget = view.license_approved_widget
        self.assertEqual('fnord-edit-license-approved', widget.content_box_id)
        self.assertEqual(
            canonical_url(self.product, view_name='+review-license'),
            widget.edit_url)

    def test_license_approved_widget_prorietary_license(self):
        # Proprietary projects cannot be approved.
        with person_logged_in(self.product.owner):
            self.product.licenses = [License.OTHER_PROPRIETARY]
        login_celebrity('registry_experts')
        view = create_initialized_view(self.product, '+index')
        text = view.license_approved_widget
        self.assertEqual('Commercial subscription required', text)

    def test_license_approved_widget_no_license(self):
        # Projects without a licence cannot be approved.
        with person_logged_in(self.product.owner):
            self.product.licenses = [License.DONT_KNOW]
        login_celebrity('registry_experts')
        view = create_initialized_view(self.product, '+index')
        text = view.license_approved_widget
        self.assertEqual('Licence required', text)

    def test_widget_id_for_name_dots(self):
        # Dots are replaced with dashes to make a valid CSS Id.
        login_celebrity('registry_experts')
        self.product.name = 'fnord.dom'
        view = create_initialized_view(self.product, '+index')
        self.assertEqual(
            'fnord-dom-edit-active',
            view.active_widget.content_box_id)
        self.assertEqual(
            'fnord-dom-edit-project-reviewed',
            view.project_reviewed_widget.content_box_id)
        self.assertEqual(
            'fnord-dom-edit-license-approved',
            view.license_approved_widget.content_box_id)

    def test_view_data_model(self):
        # The view's json request cache contains the expected data.
        view = create_initialized_view(self.product, '+index')
        cache = IJSONRequestCache(view.request)
        policy_items = [(item.name, item) for item in EXCLUSIVE_TEAM_POLICY]
        team_membership_policy_data = vocabulary_to_choice_edit_items(
            SimpleVocabulary.fromItems(policy_items),
            value_fn=lambda item: item.name)
        self.assertContentEqual(
            team_membership_policy_data,
            cache.objects['team_membership_policy_data'])

    def test_index_proprietary_specification(self):
        # Ordinary users can see page, but proprietary specs are only listed
        # for users with access to them.
        proprietary_name = 'super-private'
        proprietary = self.factory.makeSpecification(
            name=proprietary_name,
            information_type=InformationType.PROPRIETARY)
        product = removeSecurityProxy(proprietary).product
        with person_logged_in(product.owner):
            product.blueprints_usage = ServiceUsage.LAUNCHPAD
            public = self.factory.makeSpecification(product=product)
            browser = self.getViewBrowser(product, '+index')
        self.assertIn(public.name, browser.contents)
        self.assertNotIn(proprietary_name, browser.contents)
        with person_logged_in(None):
            browser = self.getViewBrowser(product, '+index',
                                          user=product.owner)
        self.assertIn(public.name, browser.contents)
        self.assertIn(proprietary_name, browser.contents)


class TestProductEditView(BrowserTestCase):
    """Tests for the ProductEditView"""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductEditView, self).setUp()

    def _make_product_edit_form(self, product, proprietary=False):
        """Return form data for product edit.

        :param product: Factory product to base the form data base of.
        """
        if proprietary:
            licenses = License.OTHER_PROPRIETARY.title
            license_info = 'Commercial Subscription'
            information_type = 'PROPRIETARY'
        else:
            licenses = ['MIT']
            license_info = ''
            information_type = 'PUBLIC'

        return {
            'field.actions.change': 'Change',
            'field.name': product.name,
            'field.display_name': product.display_name,
            'field.title': product.title,
            'field.summary': product.summary,
            'field.information_type': information_type,
            'field.licenses': licenses,
            'field.license_info': license_info,
        }

    def test_limited_information_types_allowed(self):
        """Products can only be PILLAR_INFORMATION_TYPES"""
        product = self.factory.makeProduct()
        login_person(product.owner)
        view = create_initialized_view(
            product, '+edit', principal=product.owner)
        vocabulary = view.widgets['information_type'].vocabulary
        info_types = [t.name for t in vocabulary]
        expected = ['PUBLIC', 'PROPRIETARY']
        self.assertEqual(expected, info_types)

    def test_change_information_type_proprietary(self):
        product = self.factory.makeProduct(name='fnord')
        login_person(product.owner)
        form = self._make_product_edit_form(product, proprietary=True)
        view = create_initialized_view(product, '+edit', form=form)
        self.assertEqual(0, len(view.errors))

        updated_product = getUtility(IProductSet).getByName('fnord')
        self.assertEqual(
            InformationType.PROPRIETARY, updated_product.information_type)
        # A complimentary commercial subscription is auto generated for
        # the product when the information type is changed.
        self.assertIsNotNone(updated_product.commercial_subscription)

    def test_change_information_type_proprietary_packaged(self):
        # It should be an error to make a Product private if it is packaged.
        product = self.factory.makeProduct()
        sourcepackage = self.factory.makeSourcePackage()
        sourcepackage.setPackaging(product.development_focus, product.owner)
        browser = self.getViewBrowser(product, '+edit', user=product.owner)
        info_type = browser.getControl(name='field.information_type')
        info_type.value = ['PROPRIETARY']
        old_url = browser.url
        browser.getControl('Change').click()
        self.assertEqual(old_url, browser.url)
        tag = Tag('error', 'div', text='Some series are packaged.',
                  attrs={'class': 'message'})
        self.assertThat(browser.contents, HTMLContains(tag))

    def test_multiple_info_type_errors(self):
        # Multiple information type errors are presented at once.
        product = self.factory.makeProduct()
        self.factory.makeBranch(product=product)
        self.factory.makeSpecification(product=product)
        browser = self.getViewBrowser(product, '+edit', user=product.owner)
        info_type = browser.getControl(name='field.information_type')
        info_type.value = ['PROPRIETARY']
        browser.getControl('Change').click()
        tag = Tag(
            'error', 'div', attrs={'class': 'message'},
            text='Some blueprints are public. '
                'Some branches are neither proprietary nor embargoed.')
        self.assertThat(browser.contents, HTMLContains(tag))

    def test_change_information_type_public(self):
        owner = self.factory.makePerson(name='pting')
        product = self.factory.makeProduct(
            name='fnord', information_type=InformationType.PROPRIETARY,
            owner=owner)
        login_person(owner)
        form = self._make_product_edit_form(product)
        view = create_initialized_view(product, '+edit', form=form)
        self.assertEqual(0, len(view.errors))

        updated_product = getUtility(IProductSet).getByName('fnord')
        self.assertEqual(
            InformationType.PUBLIC, updated_product.information_type)


class ProductSetReviewLicensesViewTestCase(TestCaseWithFactory):
    """Tests the ProductSetReviewLicensesView."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(ProductSetReviewLicensesViewTestCase, self).setUp()
        self.product_set = getUtility(IProductSet)
        self.user = login_celebrity('registry_experts')

    def test_initial_values(self):
        # The initial values show active, unreviewed, unapproved projects.
        view = create_initialized_view(self.product_set, '+review-licenses')
        self.assertContentEqual(
            {'active': True,
             'project_reviewed': False,
             'license_approved': False,
             'search_text': None,
             'licenses': set(),
             'has_subscription': None,
             'created_after': None,
             'created_before': None,
             'subscription_expires_after': None,
             'subscription_expires_before': None,
             'subscription_modified_after': None,
             'subscription_modified_before': None,
             }.items(),
            view.initial_values.items())

    def test_forReviewBatched(self):
        # The projects are batched.
        view = create_initialized_view(self.product_set, '+review-licenses')
        batch = view.forReviewBatched()
        self.assertEqual(50, batch.default_size)

    def test_project_common_data(self):
        # The each project contains information to complete a review.
        self.factory.makeProduct(name='fnord')
        view = create_initialized_view(
            self.product_set, '+review-licenses', principal=self.user)
        content = find_tag_by_id(view.render(), 'project-fnord')
        self.assertTrue(content.find(id='fnord-maintainer') is not None)
        self.assertTrue(content.find(id='fnord-registrant') is not None)
        self.assertTrue(content.find(id='fnord-description') is not None)
        self.assertTrue(content.find(id='fnord-packages') is not None)
        self.assertTrue(content.find(id='fnord-releases') is not None)
        self.assertTrue(content.find(id='fnord-usage') is not None)
        self.assertTrue(content.find(id='fnord-licenses') is not None)
        self.assertTrue(content.find(id='fnord-whiteboard') is not None)
        self.assertFalse(content.find(
            id='fnord-commercial-subscription') is not None)
        self.assertFalse(content.find(id='fnord-license-info') is not None)

    def test_project_license_info_data(self):
        # The projects with the OTHER_* licenese will show license_info data.
        product = self.factory.makeProduct(name='fnord')
        with person_logged_in(product.owner):
            product.licenses = [License.OTHER_OPEN_SOURCE]
        view = create_initialized_view(
            self.product_set, '+review-licenses', principal=self.user)
        content = find_tag_by_id(view.render(), 'project-fnord')
        self.assertTrue(content.find(id='fnord-license-info') is not None)

    def test_project_commercial_subscription_data(self):
        # The projects with the OTHER_Proprietary licence show commercial
        # subscription information.
        product = self.factory.makeProduct(name='fnord')
        with person_logged_in(product.owner):
            product.licenses = [License.OTHER_PROPRIETARY]
        view = create_initialized_view(
            self.product_set, '+review-licenses', principal=self.user)
        content = find_tag_by_id(view.render(), 'project-fnord')
        self.assertTrue(content.find(
            id='fnord-commercial-subscription') is not None)

    def test_project_widgets(self):
        # The active, project_reviewed, and license_approved lazrjs widgets
        # are used.
        self.factory.makeProduct(name='fnord')
        view = create_initialized_view(
            self.product_set, '+review-licenses', principal=self.user)
        content = find_tag_by_id(view.render(), 'fnord-statuses')
        self.assertTrue(
            'Y.lp.app.choice.addBinaryChoice' in str(
                content.find(id='fnord-edit-active').parent))
        self.assertTrue(
            'Y.lp.app.choice.addBinaryChoice' in str(
                content.find(id='fnord-edit-project-reviewed').parent))
        self.assertTrue(
            'Y.lp.app.choice.addBinaryChoice' in str(
                content.find(id='fnord-edit-license-approved').parent))

    def test_review_licence_query_count(self):
        # Ensure the query count is not O(n).
        for _ in range(100):
            product = self.factory.makeProduct()
            for _ in range(5):
                self.factory.makeProductReleaseFile(product=product)
        IStore(Product).invalidate()
        with StormStatementRecorder() as recorder:
            view = create_initialized_view(
                self.product_set, '+review-licenses', principal=self.user)
            view.render()
            self.assertThat(recorder, HasQueryCount(LessThan(26)))


class TestProductRdfView(BrowserTestCase):
    """Test the Product RDF view."""

    layer = DatabaseFunctionalLayer

    def test_headers(self):
        """The headers for the RDF view of a product should be as expected."""
        product = self.factory.makeProduct()
        content_disposition = 'attachment; filename="%s.rdf"' % product.name
        browser = self.getViewBrowser(product, view_name='+rdf')
        self.assertEqual(
            content_disposition, browser.headers['Content-disposition'])
        self.assertEqual(
            'application/rdf+xml', browser.headers['Content-type'])


class TestProductSet(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def makeAllInformationTypes(self):
        owner = self.factory.makePerson()
        public = self.factory.makeProduct(
            information_type=InformationType.PUBLIC, owner=owner)
        proprietary = self.factory.makeProduct(
            information_type=InformationType.PROPRIETARY, owner=owner)
        return owner, public, proprietary

    def test_proprietary_products_skipped(self):
        # Ignore proprietary products for anonymous users
        owner, public, proprietary = self.makeAllInformationTypes()
        browser = self.getViewBrowser(getUtility(IProductSet))
        with person_logged_in(owner):
            self.assertIn(public.name, browser.contents)
            self.assertNotIn(proprietary.name, browser.contents)

    def test_proprietary_products_shown_to_owners(self):
        # Owners will see their proprietary products listed
        owner, public, proprietary = self.makeAllInformationTypes()
        transaction.commit()
        browser = self.getViewBrowser(getUtility(IProductSet), user=owner)
        with person_logged_in(owner):
            self.assertIn(public.name, browser.contents)
            self.assertIn(proprietary.name, browser.contents)

    def test_proprietary_products_skipped_all(self):
        # Ignore proprietary products for anonymous users
        owner, public, proprietary = self.makeAllInformationTypes()
        product_set = getUtility(IProductSet)
        browser = self.getViewBrowser(product_set, view_name='+all')
        with person_logged_in(owner):
            self.assertIn(public.name, browser.contents)
            self.assertNotIn(proprietary.name, browser.contents)

    def test_proprietary_products_shown_to_owners_all(self):
        # Owners will see their proprietary products listed
        owner, public, proprietary = self.makeAllInformationTypes()
        transaction.commit()
        browser = self.getViewBrowser(getUtility(IProductSet), user=owner,
                view_name='+all')
        with person_logged_in(owner):
            self.assertIn(public.name, browser.contents)
            self.assertIn(proprietary.name, browser.contents)

    def test_review_exclude_proprietary_for_expert(self):
        owner, public, proprietary = self.makeAllInformationTypes()
        transaction.commit()
        expert = self.factory.makeRegistryExpert()
        browser = self.getViewBrowser(getUtility(IProductSet),
                                      view_name='+review-licenses',
                                      user=expert)
        with person_logged_in(owner):
            self.assertIn(public.name, browser.contents)
            self.assertNotIn(proprietary.name, browser.contents)

    def test_review_include_proprietary_for_admin(self):
        owner, public, proprietary = self.makeAllInformationTypes()
        transaction.commit()
        admin = self.factory.makeAdministrator()
        browser = self.getViewBrowser(getUtility(IProductSet),
                                      view_name='+review-licenses',
                                      user=admin)
        with person_logged_in(owner):
            self.assertIn(public.name, browser.contents)
            self.assertIn(proprietary.name, browser.contents)


class TestProductSetBranchView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_git_ssh_url(self):
        project = self.factory.makeProduct()
        with person_logged_in(project.owner):
            view = create_initialized_view(
                project, '+configure-code', principal=project.owner,
                method='GET')
            git_ssh_url = 'git+ssh://{username}@{host}/{project}'.format(
                username=project.owner.name,
                host=urlsplit(config.codehosting.git_ssh_root).hostname,
                project=project.name)
            self.assertEqual(git_ssh_url, view.git_ssh_url)


class TestBrowserProductSetBranchView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    editsshkeys_tag = Tag(
        'edit SSH keys', 'a', text=re.compile('register an SSH key'),
        attrs={'href': re.compile(r'/\+editsshkeys$')})

    def getBrowser(self, project, view_name=None):
        project = removeSecurityProxy(project)
        url = canonical_url(project, view_name=view_name)
        return self.getUserBrowser(url, project.owner)

    def test_no_initial_git_repository(self):
        # If a project has no default Git repository, its "Git repository"
        # control defaults to empty.
        project = self.factory.makeProduct()
        browser = self.getBrowser(project, '+configure-code')
        self.assertEqual('', browser.getControl('Git repository:').value)

    def test_initial_git_repository(self):
        # If a project has a default Git repository, its "Git repository"
        # control defaults to the unique name of that repository.
        project = self.factory.makeProduct()
        repo = self.factory.makeGitRepository(target=project)
        with person_logged_in(project.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(project, repo)
        unique_name = repo.unique_name
        browser = self.getBrowser(project, '+configure-code')
        self.assertEqual(
            unique_name, browser.getControl('Git repository:').value)

    def test_link_existing_git_repository(self):
        repo = removeSecurityProxy(self.factory.makeGitRepository(
            target=self.factory.makeProduct()))
        browser = self.getBrowser(repo.project, '+configure-code')
        browser.getControl('Git', index=0).click()
        self.assertTrue(browser.getControl(
            'Link to a Git repository already on Launchpad').selected)
        browser.getControl('Git repository:').value = repo.shortened_path
        browser.getControl('Update').click()

        tag = Tag(
            'success-div', 'div', attrs={'class': 'informational message'},
             text='Project settings updated.')
        self.assertThat(browser.contents, HTMLContains(tag))

    def test_import_git_repository_requires_feature_flag(self):
        project = self.factory.makeProduct()
        browser = self.getBrowser(project, '+configure-code')
        self.assertRaises(
            LookupError, browser.getControl,
            'Import a Git repository hosted somewhere else')

    def test_import_git_repository(self):
        self.useFixture(
            FeatureFixture({CODE_IMPORT_GIT_TARGET_FEATURE_FLAG: u'on'}))
        self.useFixture(GitHostingFixture())
        owner = self.factory.makePerson()
        project = self.factory.makeProduct(owner=owner)
        project_name = project.name
        browser = self.getBrowser(project, '+configure-code')
        browser.getControl('Git', index=0).click()
        browser.getControl(
            'Import a Git repository hosted somewhere else').click()
        self.assertEqual(
            project_name, browser.getControl('Git repository name').value)
        browser.getControl('Git repository URL').value = (
            'https://git.example.org/imported')
        browser.getControl('Update').click()

        tag = Tag(
            'success-div', 'div', attrs={'class': 'informational message'},
             text='Code import created and repository set as default.')
        self.assertThat(browser.contents, HTMLContains(tag))
        login_person(owner)
        repo = getUtility(IGitRepositorySet).getDefaultRepository(project)
        self.assertIsNotNone(repo.code_import)
        self.assertEqual(RevisionControlSystems.GIT, repo.code_import.rcs_type)
        self.assertEqual(
            'https://git.example.org/imported', repo.code_import.url)
        self.assertEqual(project.name, repo.name)

    def test_import_git_repository_bad_scheme(self):
        self.useFixture(
            FeatureFixture({CODE_IMPORT_GIT_TARGET_FEATURE_FLAG: u'on'}))
        owner = self.factory.makePerson()
        project = self.factory.makeProduct(owner=owner)
        browser = self.getBrowser(project, '+configure-code')
        browser.getControl('Git', index=0).click()
        browser.getControl(
            'Import a Git repository hosted somewhere else').click()
        browser.getControl('Git repository URL').value = (
            'svn://svn.example.org/imported')
        browser.getControl('Update').click()

        tag = Tag(
            'error', 'div', attrs={'class': 'message'},
            text=(
                'The URI scheme "svn" is not allowed.  '
                'Only URIs with the following schemes may be used: '
                'git, http, https'))
        self.assertThat(browser.contents, HTMLContains(tag))
        login_person(owner)
        self.assertIsNone(
            getUtility(IGitRepositorySet).getDefaultRepository(project))

    def test_editsshkeys_link_if_no_keys_registered(self):
        project = self.factory.makeProduct()
        browser = self.getBrowser(project, '+configure-code')
        self.assertThat(
            browser.contents, HTMLContains(self.editsshkeys_tag))

    def test_no_editsshkeys_link_if_keys_registered(self):
        project = self.factory.makeProduct()
        with person_logged_in(project.owner):
            self.factory.makeSSHKey(person=project.owner)
        browser = self.getBrowser(project, '+configure-code')
        self.assertThat(
            browser.contents,
            Not(HTMLContains(self.editsshkeys_tag)))
