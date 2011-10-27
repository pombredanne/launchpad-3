# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX: Module docstring goes here."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.person import TeamSubscriptionPolicy
from lp.testing import TestCaseWithFactory
from lp.testing.views import create_initialized_view


class TestTeamActivatePPA(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_moderated_team_has_link(self):
        team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.MODERATED)
        view = create_initialized_view(team, '+index')
        html = view()
        print "HTML: \"%s\"" % html
