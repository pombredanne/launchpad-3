# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for GitSubscriptions."""

__metaclass__ = type

from lp.app.enums import InformationType
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
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
                repository, '+addsubscriber', pricipal=owner, form=form)
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
                repository, '+addsubscriber', pricipal=owner, form=form)
            self.assertContentEqual([], view.errors)
