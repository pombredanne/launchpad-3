# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for GitSubscriptions."""

__metaclass__ = type

from urllib import urlencode

from fixtures import FakeLogger
from mechanize import LinkNotFoundError
from testtools.matchers import MatchesStructure
from zope.security.interfaces import Unauthorized

from lp.app.enums import InformationType
from lp.code.enums import (
    BranchSubscriptionDiffSize,
    BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel,
    )
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.pages import (
    extract_text,
    find_tags_by_class,
    )
from lp.testing.views import create_initialized_view


class TestGitSubscriptionAddOtherView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_cannot_subscribe_open_team_to_private_repository(self):
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            information_type=InformationType.USERDATA, owner=owner)
        team = self.factory.makeTeam()
        form = {
            'field.person': team.name,
            'field.notification_level': 'NOEMAIL',
            'field.max_diff_lines': 'NODIFF',
            'field.review_level': 'NOEMAIL',
            'field.actions.subscribe_action': 'Subscribe'}
        with person_logged_in(owner):
            view = create_initialized_view(
                repository, '+addsubscriber', principal=owner, form=form)
            self.assertContentEqual(
                ['Open and delegated teams cannot be subscribed to private '
                 'repositories.'], view.errors)

    def test_can_subscribe_open_team_to_public_repository(self):
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=owner)
        team = self.factory.makeTeam()
        form = {
            'field.person': team.name,
            'field.notification_level': 'NOEMAIL',
            'field.max_diff_lines': 'NODIFF',
            'field.review_level': 'NOEMAIL',
            'field.actions.subscribe_action': 'Subscribe'}
        with person_logged_in(owner):
            view = create_initialized_view(
                repository, '+addsubscriber', principal=owner, form=form)
            self.assertContentEqual([], view.errors)


class TestGitSubscriptionAddView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def test_requires_login(self):
        self.useFixture(FakeLogger())
        repository = self.factory.makeGitRepository()
        browser = self.getViewBrowser(repository, no_login=True)
        self.assertRaises(LinkNotFoundError, browser.getLink, 'Subscribe')
        self.assertRaises(
            Unauthorized, self.getViewBrowser,
            repository, view_name='+subscribe', no_login=True)

    def _getSubscribers(self, contents):
        subscriptions = find_tags_by_class(
            contents, 'repository-subscribers')[0]
        for subscriber in subscriptions.findAll('div'):
            yield extract_text(subscriber.renderContents())

    def _getInformationalMessage(self, contents):
        message = find_tags_by_class(contents, 'informational message')
        return extract_text(message[0])

    def test_subscribe(self):
        subscriber = self.factory.makePerson()
        repository = self.factory.makeGitRepository()
        repository.unsubscribe(repository.owner, repository.owner)
        browser = self.getViewBrowser(repository, user=subscriber)
        self.assertEqual(
            ['No subscribers.'], list(self._getSubscribers(browser.contents)))
        browser.getLink('Subscribe').click()
        browser.getControl('Notification Level').displayValue = [
            'Branch attribute notifications only']
        browser.getControl('Generated Diff Size Limit').displayValue = [
            '1000 lines']
        browser.getControl('Subscribe').click()
        self.assertTextMatchesExpressionIgnoreWhitespace(
            'You have subscribed to this repository with: '
            'Only send notifications for branch attribute changes such '
            'as name, description and whiteboard. '
            'Send email about any code review activity for this branch.',
            self._getInformationalMessage(browser.contents))
        with person_logged_in(subscriber):
            subscription = repository.getSubscription(subscriber)
        self.assertThat(subscription, MatchesStructure.byEquality(
            person=subscriber, repository=repository,
            notification_level=(
                BranchSubscriptionNotificationLevel.ATTRIBUTEONLY),
            max_diff_lines=None,
            review_level=CodeReviewNotificationLevel.FULL))

    def test_already_subscribed(self):
        repository = self.factory.makeGitRepository()
        form = {
            'field.notification_level': 'NOEMAIL',
            'field.max_diff_lines': 'NODIFF',
            'field.review_level': 'NOEMAIL',
            'field.actions.subscribe': 'Subscribe',
            }
        with person_logged_in(repository.owner):
            view = create_initialized_view(
                repository, '+subscribe', principal=repository.owner,
                form=form)
            self.assertEqual(
                ['You are already subscribed to this repository.'],
                [notification.message
                 for notification in view.request.response.notifications])

    def test_edit_subscription(self):
        subscriber = self.factory.makePerson()
        repository = self.factory.makeGitRepository()
        repository.subscribe(
            subscriber, BranchSubscriptionNotificationLevel.ATTRIBUTEONLY,
            None, CodeReviewNotificationLevel.FULL, subscriber)
        browser = self.getViewBrowser(repository, user=subscriber)
        browser.getLink('Edit your subscription').click()
        browser.getControl('Notification Level').displayValue = [
            'Branch attribute and revision notifications']
        browser.getControl('Generated Diff Size Limit').displayValue = [
            '5000 lines']
        browser.getControl('Change').click()
        self.assertTextMatchesExpressionIgnoreWhitespace(
            'Subscription updated to: '
            'Send notifications for both branch attribute updates and new '
            'revisions added to the branch. '
            'Limit the generated diff to 5000 lines. '
            'Send email about any code review activity for this branch.',
            self._getInformationalMessage(browser.contents))
        with person_logged_in(subscriber):
            subscription = repository.getSubscription(subscriber)
        self.assertThat(subscription, MatchesStructure.byEquality(
            person=subscriber, repository=repository,
            notification_level=BranchSubscriptionNotificationLevel.FULL,
            max_diff_lines=BranchSubscriptionDiffSize.FIVEKLINES,
            review_level=CodeReviewNotificationLevel.FULL))

    def test_unsubscribe(self):
        repository = self.factory.makeGitRepository()
        browser = self.getViewBrowser(repository, user=repository.owner)
        browser.getLink('Edit your subscription').click()
        form_url = browser.url
        browser.getControl('Unsubscribe').click()
        self.assertEqual(
            'You have unsubscribed from this repository.',
            self._getInformationalMessage(browser.contents))
        self.assertEqual(
            ['No subscribers.'], list(self._getSubscribers(browser.contents)))
        # Going back and then clicking on either Change or Unsubscribe gives
        # a message that we are not subscribed.
        browser.addHeader('Referer', 'https://launchpad.dev/')
        browser.open(
            form_url, data=urlencode({'field.actions.change': 'Change'}))
        self.assertEqual(
            'You are not subscribed to this repository.',
            self._getInformationalMessage(browser.contents))
        browser.open(
            form_url,
            data=urlencode({'field.actions.unsubscribe': 'Unsubscribe'}))
        self.assertEqual(
            'You are not subscribed to this repository.',
            self._getInformationalMessage(browser.contents))
