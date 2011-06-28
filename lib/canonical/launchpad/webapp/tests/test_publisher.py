# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from doctest import (
    DocTestSuite,
    ELLIPSIS,
    )
from unittest import TestLoader, TestSuite

from lazr.restful.interfaces import IJSONRequestCache
import simplejson
from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from lp.services.worlddata.interfaces.country import ICountrySet
from lp.testing import TestCaseWithFactory

from canonical.launchpad.webapp import publisher


class TestLaunchpadView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_getCacheJson_non_resource_context(self):
        view = LaunchpadView(object(), LaunchpadTestRequest())
        self.assertEqual('{}', view.getCacheJson())

    @staticmethod
    def getCanada():
        return getUtility(ICountrySet)['CA']

    def assertIsCanada(self, json_dict):
        self.assertIs(None, json_dict['description'])
        self.assertEqual('CA', json_dict['iso3166code2'])
        self.assertEqual('CAN', json_dict['iso3166code3'])
        self.assertEqual('Canada', json_dict['name'])
        self.assertIs(None, json_dict['title'])
        self.assertContentEqual(
            ['description', 'http_etag', 'iso3166code2', 'iso3166code3',
             'name', 'resource_type_link', 'self_link', 'title'],
            json_dict.keys())

    def test_getCacheJson_resource_context(self):
        view = LaunchpadView(self.getCanada(), LaunchpadTestRequest())
        json_dict = simplejson.loads(view.getCacheJson())['context']
        self.assertIsCanada(json_dict)

    def test_getCacheJson_non_resource_object(self):
        request = LaunchpadTestRequest()
        view = LaunchpadView(object(), request)
        IJSONRequestCache(request).objects['my_bool'] = True
        self.assertEqual('{"my_bool": true}', view.getCacheJson())

    def test_getCacheJson_resource_object(self):
        request = LaunchpadTestRequest()
        view = LaunchpadView(object(), request)
        IJSONRequestCache(request).objects['country'] = self.getCanada()
        self.assertIsCanada(simplejson.loads(view.getCacheJson())['country'])

    def test_getCacheJson_context_overrides_objects(self):
        request = LaunchpadTestRequest()
        view = LaunchpadView(self.getCanada(), request)
        IJSONRequestCache(request).objects['context'] = True
        self.assertIsCanada(simplejson.loads(view.getCacheJson())['context'])


def test_suite():
    suite = TestSuite()
    suite.addTest(DocTestSuite(publisher, optionflags=ELLIPSIS))
    suite.addTest(TestLoader().loadTestsFromName(__name__))
    return suite
