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
from zope.publisher.interfaces import NotFound
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.webapp.publisher import (
    FakeRequest,
    LaunchpadView,
    canonical_url)
from canonical.launchpad.webapp.servers import LaunchpadTestRequest, LaunchpadBrowserRequest
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.interfaces.person import PersonVisibility
from lp.services.features.flags import flag_info
from lp.services.features.testing import FeatureFixture
from lp.services.worlddata.interfaces.country import ICountrySet
from lp.testing import (
    logout,
    person_logged_in,
    TestCaseWithFactory,
    )

from canonical.launchpad.webapp import publisher
from lp.testing._login import login_person
from lp.testing.publication import test_traverse


class TestLaunchpadView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestLaunchpadView, self).setUp()
        flag_info.append(
            ('test_feature', 'boolean', 'documentation', 'default_value_1',
             'title', 'http://wiki.lp.dev/LEP/sample'))
        flag_info.append(
            ('test_feature_2', 'boolean', 'documentation', 'default_value_2',
             'title', 'http://wiki.lp.dev/LEP/sample2'))

    def tearDown(self):
        flag_info.pop()
        flag_info.pop()
        super(TestLaunchpadView, self).tearDown()

    def test_getCacheJSON_non_resource_context(self):
        view = LaunchpadView(object(), LaunchpadTestRequest())
        self.assertEqual('{"related_features": {}}', view.getCacheJSON())

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

    def test_getCacheJSON_resource_context(self):
        view = LaunchpadView(self.getCanada(), LaunchpadTestRequest())
        json_dict = simplejson.loads(view.getCacheJSON())['context']
        self.assertIsCanada(json_dict)

    def test_getCacheJSON_non_resource_object(self):
        request = LaunchpadTestRequest()
        view = LaunchpadView(object(), request)
        IJSONRequestCache(request).objects['my_bool'] = True
        with person_logged_in(self.factory.makePerson()):
            self.assertEqual(
                '{"related_features": {}, "my_bool": true}',
                view.getCacheJSON())

    def test_getCacheJSON_resource_object(self):
        request = LaunchpadTestRequest()
        view = LaunchpadView(object(), request)
        IJSONRequestCache(request).objects['country'] = self.getCanada()
        with person_logged_in(self.factory.makePerson()):
            json_dict = simplejson.loads(view.getCacheJSON())['country']
        self.assertIsCanada(json_dict)

    def test_getCacheJSON_context_overrides_objects(self):
        request = LaunchpadTestRequest()
        view = LaunchpadView(self.getCanada(), request)
        IJSONRequestCache(request).objects['context'] = True
        with person_logged_in(self.factory.makePerson()):
            json_dict = simplejson.loads(view.getCacheJSON())['context']
        self.assertIsCanada(json_dict)

    def test_getCache_anonymous(self):
        request = LaunchpadTestRequest()
        view = LaunchpadView(self.getCanada(), request)
        self.assertIs(None, view.user)
        IJSONRequestCache(request).objects['my_bool'] = True
        json_dict = simplejson.loads(view.getCacheJSON())
        self.assertIsCanada(json_dict['context'])
        self.assertIn('my_bool', json_dict)

    def test_getCache_anonymous_obfuscated(self):
        request = LaunchpadTestRequest()
        branch = self.factory.makeBranch(name='user@domain')
        logout()
        view = LaunchpadView(branch, request)
        self.assertIs(None, view.user)
        self.assertNotIn('user@domain', view.getCacheJSON())

    def test_related_feature_info__default(self):
        # By default, LaunchpadView.related_feature_info is empty.
        request = LaunchpadTestRequest()
        view = LaunchpadView(object(), request)
        self.assertEqual(0, len(view.related_feature_info))

    def test_related_feature_info__with_related_feature_nothing_enabled(self):
        # If a view has a non-empty sequence of related feature flags but if
        # no matching feature rules are defined, is_beta is False.
        request = LaunchpadTestRequest()
        view = LaunchpadView(object(), request)
        view.related_features = ['test_feature']
        self.assertEqual({
            'test_feature': {
                'is_beta': False,
                'title': 'title',
                'url': 'http://wiki.lp.dev/LEP/sample',
                'value': None,
            }
        }, view.related_feature_info)

    def test_related_feature_info__default_scope_only(self):
        # If a view has a non-empty sequence of related feature flags but if
        # only a default scope is defined, it is not considered beta.
        self.useFixture(FeatureFixture(
            {},
            (
                {
                    u'flag': u'test_feature',
                    u'scope': u'default',
                    u'priority': 0,
                    u'value': u'on',
                    },
                )))
        request = LaunchpadTestRequest()
        view = LaunchpadView(object(), request)
        view.related_features = ['test_feature']
        self.assertEqual({'test_feature': {
            'is_beta': False,
            'title': 'title',
            'url': 'http://wiki.lp.dev/LEP/sample',
            'value': 'on',
        }}, view.related_feature_info)

    def test_active_related_features__enabled_feature(self):
        # If a view has a non-empty sequence of related feature flags and if
        # only a non-default scope is defined and active, the property
        # active_related_features contains this feature flag.
        self.useFixture(FeatureFixture(
            {},
            (
                {
                    u'flag': u'test_feature',
                    u'scope': u'pageid:foo',
                    u'priority': 0,
                    u'value': u'on',
                    },
                )))
        request = LaunchpadTestRequest()
        view = LaunchpadView(object(), request)
        view.related_features = ['test_feature']
        self.assertEqual({
            'test_feature': {
                'is_beta': True,
                'title': 'title',
                'url': 'http://wiki.lp.dev/LEP/sample',
                'value': 'on'}
            },
            view.related_feature_info)

    def makeFeatureFlagDictionaries(self, default_value, scope_value):
        # Return two dictionaries describing a feature for each test feature.
        # One dictionary specifies the default value, the other specifies
        # a more restricted scope.
        def makeFeatureDict(flag, value, scope, priority):
            return {
                u'flag': flag,
                u'scope': scope,
                u'priority': priority,
                u'value': value,
                }
        return (
            makeFeatureDict('test_feature', default_value, u'default', 0),
            makeFeatureDict('test_feature', scope_value, u'pageid:foo', 10),
            makeFeatureDict('test_feature_2', default_value, u'default', 0),
            makeFeatureDict('test_feature_2', scope_value, u'pageid:bar', 10))

    def test_related_features__enabled_feature_with_default(self):
        # If a view
        #   * has a non-empty sequence of related feature flags,
        #   * the default scope and a non-default scope are defined
        #     but have different values,
        # then the property related_feature_info contains this feature flag.
        self.useFixture(FeatureFixture(
            {}, self.makeFeatureFlagDictionaries(u'', u'on')))
        request = LaunchpadTestRequest()
        view = LaunchpadView(object(), request)
        view.related_features = ['test_feature']
        self.assertEqual({
            'test_feature': {
                'is_beta': True,
                'title': 'title',
                'url': 'http://wiki.lp.dev/LEP/sample',
                'value': 'on',
            }},
            view.related_feature_info)

    def test_related_feature_info__enabled_feature_with_default_same_value(
        self):
        # If a view
        #   * has a non-empty sequence of related feature flags,
        #   * the default scope and a non-default scope are defined
        #     and have the same values,
        # then is_beta is false.
        self.useFixture(FeatureFixture(
            {}, self.makeFeatureFlagDictionaries(u'on', u'on')))
        request = LaunchpadTestRequest()
        view = LaunchpadView(object(), request)
        view.related_features = ['test_feature']
        self.assertEqual({'test_feature': {
            'is_beta': False,
            'title': 'title',
            'url': 'http://wiki.lp.dev/LEP/sample',
            'value': 'on',
        }}, view.related_feature_info)

    def test_json_cache_has_related_features(self):
        # The property related_features is copied into the JSON cache.
        class TestView(LaunchpadView):
            related_features = ['test_feature']

        self.useFixture(FeatureFixture(
            {}, self.makeFeatureFlagDictionaries(u'', u'on')))
        request = LaunchpadTestRequest()
        view = TestView(object(), request)
        with person_logged_in(self.factory.makePerson()):
            self.assertEqual(
                '{"related_features": {"test_feature": {'
                '"url": "http://wiki.lp.dev/LEP/sample", '
                '"is_beta": true, '
                '"value": "on", '
                '"title": "title"'
                '}}}',
                view.getCacheJSON())

    def test_json_cache_collects_related_features_from_all_views(self):
        # A typical page includes data from more than one view,
        # for example, from macros. Related features from these sub-views
        # are included in the JSON cache.
        class TestView(LaunchpadView):
            related_features = ['test_feature']

        class TestView2(LaunchpadView):
            related_features = ['test_feature_2']

        self.useFixture(FeatureFixture(
            {}, self.makeFeatureFlagDictionaries(u'', u'on')))
        request = LaunchpadTestRequest()
        view = TestView(object(), request)
        TestView2(object(), request)
        with person_logged_in(self.factory.makePerson()):
            self.assertEqual(
                '{"related_features": '
                '{"test_feature_2": {"url": "http://wiki.lp.dev/LEP/sample2",'
                ' "is_beta": true, "value": "on", "title": "title"}, '
                '"test_feature": {"url": "http://wiki.lp.dev/LEP/sample", '
                '"is_beta": true, "value": "on", "title": "title"}}}',
                view.getCacheJSON())

    def test_view_creation_with_fake_or_none_request(self):
        # LaunchpadView.__init__() does not crash with a FakeRequest.
        LaunchpadView(object(), FakeRequest())
        # Or when no request at all is passed.
        LaunchpadView(object(), None)


class TestPersonTraversal(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_private_team_visible_to_admin_and_members_only(self):
        # Verify traversal to private teams.
        name = 'private-team'
        team = self.factory.makeTeam(name=name)
        team_url = canonical_url(team)
        admin = getUtility(ILaunchpadCelebrities).admin.teamowner
        login_person(admin)
        team.visibility = PersonVisibility.PRIVATE

        # Admins can traverse to the team.
        obj, view, req = test_traverse(team_url)
        self.assertEqual(team, obj)

        # Members can traverse to the team.
        login_person(team.teamowner)
        obj, view, req = test_traverse(team_url)
        self.assertEqual(team, obj)

        # All other user cannot traverse to the team.
        login_person(self.factory.makePerson())
        self.assertRaises(NotFound, test_traverse, team_url)


def test_suite():
    suite = TestSuite()
    suite.addTest(DocTestSuite(publisher, optionflags=ELLIPSIS))
    suite.addTest(TestLoader().loadTestsFromName(__name__))
    return suite
