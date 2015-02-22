# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the Person/DistributionSourcePackage non-database class."""

__metaclass__ = type

from lp.registry.model.persondistributionsourcepackage import (
    PersonDistributionSourcePackage,
    )
from lp.services.webapp.interfaces import IBreadcrumb
from lp.services.webapp.publisher import canonical_url
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestPersonDistributionSourcePackage(TestCaseWithFactory):
    """Tests for `IPersonDistributionSourcePackage`s."""

    layer = DatabaseFunctionalLayer

    def _makePersonDistributionSourcePackage(self):
        person = self.factory.makePerson()
        dsp = self.factory.makeDistributionSourcePackage()
        return PersonDistributionSourcePackage(person, dsp)

    def test_canonical_url(self):
        # The canonical_url of a person DSP is
        # ~person/distribution/+source/sourcepackagename.
        pdsp = self._makePersonDistributionSourcePackage()
        dsp = pdsp.distro_source_package
        expected = 'http://launchpad.dev/~%s/%s/+source/%s' % (
            pdsp.person.name, dsp.distribution.name,
            dsp.sourcepackagename.name)
        self.assertEqual(expected, canonical_url(pdsp))

    def test_breadcrumb(self):
        # Person DSPs give the DSP as their breadcrumb url.
        pdsp = self._makePersonDistributionSourcePackage()
        breadcrumb = IBreadcrumb(pdsp, None)
        self.assertEqual(
            canonical_url(pdsp.distro_source_package), breadcrumb.url)
