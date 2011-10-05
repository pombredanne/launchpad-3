# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for interaction helpers."""

__metaclass__ = type

from zope.security.interfaces import IParticipation

from canonical.launchpad.webapp.interaction import Participation
from canonical.launchpad.webapp.interfaces import IParticipationExtras
from canonical.testing.layers import BaseLayer
from lp.testing import TestCase


class TestParticipationInterfaces(TestCase):
    layer = BaseLayer

    def test_Participation_implements_IParticipation(self):
        self.assertProvides(Participation(), IParticipation)

    def test_Participation_implements_IParticipationExtras(self):
        self.assertProvides(Participation(), IParticipationExtras)
