# Copyright 2011-2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the builders webservice ."""

__metaclass__ = type

from json import dumps

from testtools.matchers import Equals
from zope.component import getUtility

from lp.registry.interfaces.person import IPersonSet
from lp.services.webapp import canonical_url
from lp.services.webapp.interfaces import OAuthPermission
from lp.testing import (
    admin_logged_in,
    api_url,
    logout,
    RequestTimelineCollector,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount
from lp.testing.pages import (
    LaunchpadWebServiceCaller,
    webservice_for_person,
    )


class TestBuildersCollection(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBuildersCollection, self).setUp()
        self.webservice = LaunchpadWebServiceCaller()

    def test_list(self):
        names = ['bob', 'frog']
        for i in range(3):
            builder = self.factory.makeBuilder()
            self.factory.makeBinaryPackageBuild().queueBuild().markAsBuilding(
                builder)
            names.append(builder.name)
        logout()
        with RequestTimelineCollector() as recorder:
            builders = self.webservice.get(
                '/builders', api_version='devel').jsonBody()
        self.assertContentEqual(
            names, [b['name'] for b in builders['entries']])
        self.assertThat(recorder, HasQueryCount(Equals(19)))

    def test_list_with_private_builds(self):
        # Inaccessible private builds aren't linked in builders'
        # current_build fields.
        with admin_logged_in():
            rbpb = self.factory.makeBinaryPackageBuild(
                archive=self.factory.makeArchive(private=True))
            rbpb.queueBuild().markAsBuilding(
                self.factory.makeBuilder(name='restricted'))
            bpb = self.factory.makeBinaryPackageBuild(
                archive=self.factory.makeArchive(private=False))
            bpb.queueBuild().markAsBuilding(
                self.factory.makeBuilder(name='public'))
            bpb_url = canonical_url(bpb, path_only_if_possible=True)
        logout()

        builders = self.webservice.get(
            '/builders', api_version='devel').jsonBody()
        current_builds = dict(
            (b['name'], b['current_build_link']) for b in builders['entries'])
        self.assertEqual(
            'tag:launchpad.net:2008:redacted', current_builds['restricted'])
        self.assertEqual(
            'http://api.launchpad.dev/devel' + bpb_url,
            current_builds['public'])

    def test_getBuildQueueSizes(self):
        logout()
        results = self.webservice.named_get(
            '/builders', 'getBuildQueueSizes', api_version='devel')
        self.assertEqual(
            ['nonvirt', 'virt'], sorted(results.jsonBody().keys()))

    def test_getBuildersForQueue(self):
        g1 = self.factory.makeProcessor('g1')
        quantum = self.factory.makeProcessor('quantum')
        self.factory.makeBuilder(
            processors=[quantum], name='quantum_builder1')
        self.factory.makeBuilder(
            processors=[quantum], name='quantum_builder2')
        self.factory.makeBuilder(
            processors=[quantum], name='quantum_builder3', virtualized=False)
        self.factory.makeBuilder(
            processors=[g1], name='g1_builder', virtualized=False)

        logout()
        results = self.webservice.named_get(
            '/builders', 'getBuildersForQueue',
            processor=api_url(quantum), virtualized=True,
            api_version='devel').jsonBody()
        self.assertEqual(
            ['quantum_builder1', 'quantum_builder2'],
            sorted(builder['name'] for builder in results['entries']))

    def test_new(self):
        person = self.factory.makePerson()
        badmins = getUtility(IPersonSet).getByName('launchpad-buildd-admins')
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PRIVATE)
        args = dict(
            name='foo', processors=['/+processors/386'], title='foobar',
            url='http://foo.buildd:8221/', virtualized=False,
            api_version='devel')

        response = webservice.named_post('/builders', 'new', **args)
        self.assertEqual(401, response.status)

        with admin_logged_in():
            badmins.addMember(person, badmins)
        response = webservice.named_post('/builders', 'new', **args)
        self.assertEqual(201, response.status)

        self.assertEqual(
            'foobar', webservice.get('/builders/foo').jsonBody()['title'])


class TestBuilderEntry(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBuilderEntry, self).setUp()
        self.webservice = LaunchpadWebServiceCaller()

    def test_security(self):
        # Attributes can only be set by buildd admins.
        builder = self.factory.makeBuilder()
        user = self.factory.makePerson()
        user_webservice = webservice_for_person(
            user, permission=OAuthPermission.WRITE_PUBLIC)
        patch = dumps({'clean_status': 'Cleaning'})
        logout()

        # A normal user is unauthorized.
        response = user_webservice.patch(
            api_url(builder), 'application/json', patch, api_version='devel')
        self.assertEqual(401, response.status)

        # But a buildd admin can set the attribute.
        with admin_logged_in():
            buildd_admins = getUtility(IPersonSet).getByName(
                'launchpad-buildd-admins')
            buildd_admins.addMember(user, buildd_admins.teamowner)
        response = user_webservice.patch(
            api_url(builder), 'application/json', patch, api_version='devel')
        self.assertEqual(209, response.status)
        self.assertEqual('Cleaning', response.jsonBody()['clean_status'])

    def test_exports_processor(self):
        processor = self.factory.makeProcessor('s1')
        builder = self.factory.makeBuilder(processors=[processor])

        logout()
        entry = self.webservice.get(
            api_url(builder), api_version='devel').jsonBody()
        self.assertEndsWith(entry['processor_link'], '/+processors/s1')

    def test_getBuildRecords(self):
        builder = self.factory.makeBuilder()
        build = self.factory.makeBinaryPackageBuild(builder=builder)
        build_title = build.title

        logout()
        results = self.webservice.named_get(
            api_url(builder), 'getBuildRecords', pocket='Release',
            api_version='devel').jsonBody()
        self.assertEqual(
            [build_title], [entry['title'] for entry in results['entries']])
        results = self.webservice.named_get(
            api_url(builder), 'getBuildRecords', pocket='Proposed',
            api_version='devel').jsonBody()
        self.assertEqual(0, len(results['entries']))
