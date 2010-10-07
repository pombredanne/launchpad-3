# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test distributionsourcepackage views."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import test_tales, TestCaseWithFactory


class TestDistributionSourcePackageFormatterAPI(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_link(self):
        sourcepackagename = self.factory.makeSourcePackageName('mouse')
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        dsp = ubuntu.getSourcePackage('mouse')
        markup = (
            u'<a href="/ubuntu/+source/mouse" class="sprite package-source">'
            u'mouse in ubuntu</a>')
        self.assertEqual(markup, test_tales('dsp/fmt:link', dsp=dsp))
