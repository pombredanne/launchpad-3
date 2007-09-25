# Copyright 2006 Canonical Ltd.  All rights reserved.

import unittest

from BeautifulSoup import BeautifulSoup
from zope.component import getUtility

from canonical.launchpad.browser.productseries import ProductSeriesSourceView
from canonical.launchpad.ftests.harness import login, logout, ANONYMOUS
from canonical.launchpad.interfaces import IProductSet, RevisionControlSystems
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadFunctionalLayer


class RcsTypeWidgetDisectionTestCase(unittest.TestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login(ANONYMOUS)

    def tearDown(self):
        logout()

    def testDisectRcsTypeWidget(self):
        # Test that the rcstype widget is disected correctly
        product = getUtility(IProductSet).getByName('firefox')
        context = product.getSeries('trunk')
        request = LaunchpadTestRequest()
        self.assertEqual(context.rcstype, None)

        view = ProductSeriesSourceView(context, request)
        view.setUpFields()
        view.setUpWidgets()
        self.assertInputElement(
            view.rcstype_none, 'radio', 'field.rcstype', '', checked=True)
        self.assertInputElement(
            view.rcstype_cvs, 'radio', 'field.rcstype',
            RevisionControlSystems.CVS.name, checked=False)
        self.assertInputElement(
            view.rcstype_svn, 'radio', 'field.rcstype',
            RevisionControlSystems.SVN.name, checked=False)
        self.assertInputElement(
            view.rcstype_emptymarker, 'hidden', 'field.rcstype-empty-marker',
            '1')

        # Now check a productseries with a different rcstype.
        product = getUtility(IProductSet).getByName('evolution')
        context = product.getSeries('trunk')
        self.assertEqual(context.rcstype, RevisionControlSystems.CVS)

        view = ProductSeriesSourceView(context, request)
        view.setUpFields()
        view.setUpWidgets()
        self.assertInputElement(
            view.rcstype_none, 'radio', 'field.rcstype', '', checked=False)
        self.assertInputElement(
            view.rcstype_cvs, 'radio', 'field.rcstype',
            RevisionControlSystems.CVS.name, checked=True)

    def assertInputElement(self, data, type, name, value, checked=False):
        soup = BeautifulSoup(data)
        self.assertEqual(len(soup), 1)
        input = soup.first()
        self.assertEqual(input.name, 'input')
        self.assertEqual(input['type'], type)
        self.assertEqual(input['name'], name)
        self.assertEqual(input['value'], value)
        self.assertEqual(input.has_key('checked'), checked)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
