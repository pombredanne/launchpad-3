# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.services.profile.

See lib/canonical/doc/profiling.txt for an end-user description of
the functionality.
"""

__metaclass__ = type

import glob
import os
import time
import unittest

from lp.testing import TestCase
from bzrlib.lsprof import BzrProfiler
from zope.app.publication.interfaces import (
    BeforeTraverseEvent,
    EndRequestEvent,
    )
from zope.component import getSiteManager

import canonical.launchpad.webapp.adapter as da
from canonical.launchpad.webapp.errorlog import (
    ErrorReport,
    ErrorReportingUtility,
    )
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.launchpad.webapp.interfaces import StartRequestEvent
from canonical.testing import layers
from lp.services.features.testing import FeatureFixture
from lp.services.profile import profile

EXAMPLE_HTML_START = '''\
<html><head><title>Random!</title></head>
<body>
<h1>Random!</h1>
<p>Whatever!</p>
'''
EXAMPLE_HTML_END = '''\
</body>
</html>
'''
EXAMPLE_HTML = EXAMPLE_HTML_START + EXAMPLE_HTML_END


class BaseTest(TestCase):

    def _get_request(self, path='/'):
        """Return a test request for the given path."""
        return LaunchpadTestRequest(PATH_INFO=path)

    def _get_start_event(self, path='/'):
        """Return a start event for the given path."""
        return StartRequestEvent(self._get_request(path))

    def assertCleanProfilerState(self, message='something did not clean up'):
        """Check whether profiler thread local is clean."""
        for name in ('profiler', 'actions', 'memory_profile_start'):
            self.assertIs(
                getattr(profile._profilers, name, None), None,
                'Profiler state (%s) is dirty; %s.' % (name, message))

    def pushProfilingConfig(
        self, profiling_allowed='False', profile_all_requests='False',
        memory_profile_log=''):
        """This is a convenience for setting profile configs."""
        self.pushConfig(
            'profiling',
            profiling_allowed=profiling_allowed,
            profile_all_requests=profile_all_requests,
            memory_profile_log=memory_profile_log)


class TestCleanupProfiler(BaseTest):
    """Add a tearDown that will cleanup the profiler if it is running."""

    def tearDown(self):
        "Do the usual tearDown, plus clean up the profiler object."
        if getattr(profile._profilers, 'profiler', None) is not None:
            profile._profilers.profiler.stop()
            del profile._profilers.profiler
        for name in ('actions', 'memory_profile_start', 'profiling'):
            if getattr(profile._profilers, name, None) is not None:
                delattr(profile._profilers, name)
        super(TestCleanupProfiler, self).tearDown()


class TestRequestStartHandler(TestCleanupProfiler):
    """Tests for the start handler of the profiler integration.

    See lib/canonical/doc/profiling.txt for an end-user description of
    the functionality.
    """

    def test_config_stops_profiling(self):
        """The ``profiling_allowed`` configuration should disable all
        profiling, even if it is requested"""
        self.pushProfilingConfig(
            profiling_allowed='False', profile_all_requests='True',
            memory_profile_log='.')
        profile.start_request(self._get_start_event('/++profile++show,log'))
        self.assertCleanProfilerState('config was ignored')

    def test_optional_profiling_without_marked_request_has_no_profile(self):
        """Even if profiling is allowed, it does not happen with a normal
        request."""
        self.pushProfilingConfig(profiling_allowed='True')
        profile.start_request(self._get_start_event('/'))
        self.assertEqual(profile._profilers.actions, set())
        self.assertIs(getattr(profile._profilers, 'profiler', None), None)
        self.assertIs(
            getattr(profile._profilers, 'memory_profile_start', None), None)

    def test_optional_profiling_with_show_request_starts_profiling(self):
        """If profiling is allowed and a request with the "show" marker
        URL segment is made, profiling starts."""
        self.pushProfilingConfig(profiling_allowed='True')
        profile.start_request(self._get_start_event('/++profile++show/'))
        self.assertIsInstance(profile._profilers.profiler, BzrProfiler)
        self.assertIs(
            getattr(profile._profilers, 'memory_profile_start', None),
            None)
        self.assertEquals(profile._profilers.actions, set(('show', )))

    def test_optional_profiling_with_log_request_starts_profiling(self):
        """If profiling is allowed and a request with the "log" marker
        URL segment is made, profiling starts."""
        self.pushProfilingConfig(profiling_allowed='True')
        profile.start_request(self._get_start_event('/++profile++log/'))
        self.assertIsInstance(profile._profilers.profiler, BzrProfiler)
        self.assertIs(
            getattr(profile._profilers, 'memory_profile_start', None),
            None)
        self.assertEquals(profile._profilers.actions, set(('log', )))

    def test_optional_profiling_with_combined_request_starts_profiling(self):
        """If profiling is allowed and a request with the "log" and
        "show" marker URL segment is made, profiling starts."""
        self.pushProfilingConfig(profiling_allowed='True')
        profile.start_request(self._get_start_event('/++profile++log,show/'))
        self.assertIsInstance(profile._profilers.profiler, BzrProfiler)
        self.assertIs(
            getattr(profile._profilers, 'memory_profile_start', None),
            None)
        self.assertEquals(profile._profilers.actions, set(('log', 'show')))

    def test_optional_profiling_with_reversed_request_starts_profiling(self):
        """If profiling is allowed and a request with the "show" and
        "log" marker URL segment is made, profiling starts."""
        self.pushProfilingConfig(profiling_allowed='True')
        # The fact that this is reversed from the previous request is the only
        # difference from the previous test.  Also, it doesn't have a
        # trailing slash. :-P
        profile.start_request(self._get_start_event('/++profile++show,log'))
        self.assertIsInstance(profile._profilers.profiler, BzrProfiler)
        self.assertIs(
            getattr(profile._profilers, 'memory_profile_start', None),
            None)
        self.assertEquals(profile._profilers.actions, set(('log', 'show')))

    def test_forced_profiling_registers_action(self):
        """profile_all_requests should register as a log action"""
        self.pushProfilingConfig(
            profiling_allowed='True', profile_all_requests='True')
        profile.start_request(self._get_start_event('/'))
        self.assertIsInstance(profile._profilers.profiler, BzrProfiler)
        self.assertIs(
            getattr(profile._profilers, 'memory_profile_start', None),
            None)
        self.assertEquals(profile._profilers.actions, set(('log', )))

    def test_optional_profiling_with_wrong_request_helps(self):
        """If profiling is allowed and a request with the marker URL segment
        is made incorrectly, profiling does not start and help is an action.
        """
        self.pushProfilingConfig(profiling_allowed='True')
        profile.start_request(self._get_start_event('/++profile++/'))
        self.assertIs(getattr(profile._profilers, 'profiler', None), None)
        self.assertIs(
            getattr(profile._profilers, 'memory_profile_start', None),
            None)
        self.assertEquals(profile._profilers.actions, set(('help', )))

    def test_forced_profiling_with_wrong_request_helps(self):
        """If profiling is forced and a request with the marker URL segment
        is made incorrectly, profiling starts and help is an action.
        """
        self.pushProfilingConfig(
            profiling_allowed='True', profile_all_requests='True')
        profile.start_request(self._get_start_event('/++profile++/'))
        self.assertIsInstance(profile._profilers.profiler, BzrProfiler)
        self.assertIs(
            getattr(profile._profilers, 'memory_profile_start', None),
            None)
        self.assertEquals(profile._profilers.actions, set(('help', 'log')))

    def test_memory_profile_start(self):
        self.pushProfilingConfig(
            profiling_allowed='True', memory_profile_log='.')
        profile.start_request(self._get_start_event('/'))
        self.assertIs(getattr(profile._profilers, 'profiler', None), None)
        self.assertIsInstance(profile._profilers.memory_profile_start, tuple)
        self.assertEqual(len(profile._profilers.memory_profile_start), 2)
        self.assertEqual(profile._profilers.actions, set())

    def test_combo_memory_and_profile_start(self):
        self.pushProfilingConfig(
            profiling_allowed='True', memory_profile_log='.')
        profile.start_request(self._get_start_event('/++profile++show/'))
        self.assertIsInstance(profile._profilers.profiler, BzrProfiler)
        self.assertIsInstance(profile._profilers.memory_profile_start, tuple)
        self.assertEqual(len(profile._profilers.memory_profile_start), 2)
        self.assertEquals(profile._profilers.actions, set(('show', )))


class TestRequestEndHandler(BaseTest):
    """Tests for the end-request handler.

    If the start-request handler is broken, these tests will fail too, so fix
    the tests in the above test case first.

    See lib/canonical/doc/profiling.txt for an end-user description
    of the functionality.
    """

    def setUp(self):
        TestCase.setUp(self)
        self.patch(da, 'get_request_start_time', time.time)
        self.patch(da, 'get_request_duration', lambda: 0.5)
        self.profile_dir = self.makeTemporaryDirectory()
        self.memory_profile_log = os.path.join(self.profile_dir, 'memory_log')
        self.pushConfig('profiling', profile_dir=self.profile_dir)
        self.eru = ErrorReportingUtility()
        sm = getSiteManager()
        sm.registerUtility(self.eru)
        self.addCleanup(sm.unregisterUtility, self.eru)

    def _get_end_event(self, path='/', result=EXAMPLE_HTML, pageid=None):
        """Return a stop event for the given path and output HTML."""
        start_event = self._get_start_event(path)
        profile.start_request(start_event)
        request = start_event.request
        if pageid is not None:
            request.setInWSGIEnvironment('launchpad.pageid', pageid)
        request.response.setResult(result)
        context = object()
        return EndRequestEvent(context, request)

    def endRequest(self, path='/', exception=None, pageid=None):
        event = self._get_end_event(path, pageid=pageid)
        if exception is not None:
            self.eru.raising(
                (type(exception), exception, None), event.request)
        profile.end_request(event)
        return event.request

    def getAddedResponse(self, request,
                         start=EXAMPLE_HTML_START, end=EXAMPLE_HTML_END):
        output = request.response.consumeBody()
        return output[len(start):-len(end)]

    def getMemoryLog(self):
        if not os.path.exists(self.memory_profile_log):
            return []
        f = open(self.memory_profile_log)
        result = f.readlines()
        f.close()
        return result

    def getProfilePaths(self):
        return glob.glob(os.path.join(self.profile_dir, '*.prof'))

    #########################################################################
    # Tests
    def test_config_stops_profiling(self):
        """The ``profiling_allowed`` configuration should disable all
        profiling, even if it is requested"""
        self.pushProfilingConfig(
            profiling_allowed='False', profile_all_requests='True',
            memory_profile_log=self.memory_profile_log)
        request = self.endRequest('/++profile++show,log')
        self.assertIs(getattr(request, 'oops', None), None)
        self.assertEqual(self.getAddedResponse(request), '')
        self.assertEqual(self.getMemoryLog(), [])
        self.assertEqual(self.getProfilePaths(), [])
        self.assertCleanProfilerState()

    def test_optional_profiling_without_marked_request_has_no_profile(self):
        """Even if profiling is allowed, it does not happen with a normal
        request."""
        self.pushProfilingConfig(profiling_allowed='True')
        request = self.endRequest('/')
        self.assertIs(getattr(request, 'oops', None), None)
        self.assertEqual(self.getAddedResponse(request), '')
        self.assertEqual(self.getMemoryLog(), [])
        self.assertEqual(self.getProfilePaths(), [])
        self.assertCleanProfilerState()

    def test_optional_profiling_with_show_request_profiles(self):
        """If profiling is allowed and a request with the "show" marker
        URL segment is made, profiling starts."""
        self.pushProfilingConfig(profiling_allowed='True')
        request = self.endRequest('/++profile++show/')
        self.assertIsInstance(request.oops, ErrorReport)
        self.assertIn('Top Inline Time', self.getAddedResponse(request))
        self.assertEqual(self.getMemoryLog(), [])
        self.assertEqual(self.getProfilePaths(), [])
        self.assertCleanProfilerState()

    def test_optional_profiling_with_log_request_profiles(self):
        """If profiling is allowed and a request with the "log" marker
        URL segment is made, profiling starts."""
        self.pushProfilingConfig(profiling_allowed='True')
        request = self.endRequest('/++profile++log/')
        self.assertIsInstance(request.oops, ErrorReport)
        response = self.getAddedResponse(request)
        self.assertIn('Profile was logged to', response)
        self.assertNotIn('Top Inline Time', response)
        self.assertEqual(self.getMemoryLog(), [])
        paths = self.getProfilePaths()
        self.assertEqual(len(paths), 1)
        self.assertIn(paths[0], response)
        self.assertCleanProfilerState()

    def test_optional_profiling_with_combined_request_profiles(self):
        """If profiling is allowed and a request with the "log" and
        "show" marker URL segment is made, profiling starts."""
        self.pushProfilingConfig(profiling_allowed='True')
        request = self.endRequest('/++profile++log,show')
        self.assertIsInstance(request.oops, ErrorReport)
        response = self.getAddedResponse(request)
        self.assertIn('Profile was logged to', response)
        self.assertIn('Top Inline Time', response)
        self.assertEqual(self.getMemoryLog(), [])
        paths = self.getProfilePaths()
        self.assertEqual(len(paths), 1)
        self.assertIn(paths[0], response)
        self.assertCleanProfilerState()

    def test_forced_profiling_logs(self):
        """profile_all_requests should register as a log action"""
        self.pushProfilingConfig(
            profiling_allowed='True', profile_all_requests='True')
        request = self.endRequest('/')
        self.assertIsInstance(request.oops, ErrorReport)
        response = self.getAddedResponse(request)
        self.assertIn('Profile was logged to', response)
        self.assertIn('profile_all_requests: True', response)
        self.assertNotIn('Top Inline Time', response)
        self.assertEqual(self.getMemoryLog(), [])
        paths = self.getProfilePaths()
        self.assertEqual(len(paths), 1)
        self.assertIn(paths[0], response)
        self.assertCleanProfilerState()

    def test_optional_profiling_with_wrong_request_helps(self):
        """If profiling is allowed and a request with the marker URL segment
        is made incorrectly, profiling does not start and help is an action.
        """
        self.pushProfilingConfig(profiling_allowed='True')
        request = self.endRequest('/++profile++')
        self.assertIs(getattr(request, 'oops', None), None)
        response = self.getAddedResponse(request)
        self.assertIn('<h2>Help</h2>', response)
        self.assertNotIn('Top Inline Time', response)
        self.assertEqual(self.getMemoryLog(), [])
        self.assertEqual(self.getProfilePaths(), [])
        self.assertCleanProfilerState()

    def test_forced_profiling_with_wrong_request_helps(self):
        """If profiling is forced and a request with the marker URL segment
        is made incorrectly, profiling starts and help is an action.
        """
        self.pushProfilingConfig(
            profiling_allowed='True', profile_all_requests='True')
        request = self.endRequest('/++profile++')
        self.assertIsInstance(request.oops, ErrorReport)
        response = self.getAddedResponse(request)
        self.assertIn('<h2>Help</h2>', response)
        self.assertIn('Profile was logged to', response)
        self.assertIn('profile_all_requests: True', response)
        self.assertNotIn('Top Inline Time', response)
        self.assertEqual(self.getMemoryLog(), [])
        paths = self.getProfilePaths()
        self.assertEqual(len(paths), 1)
        self.assertIn(paths[0], response)
        self.assertCleanProfilerState()

    def test_memory_profile(self):
        "Does the memory profile work?"
        self.pushProfilingConfig(
            profiling_allowed='True',
            memory_profile_log=self.memory_profile_log)
        request = self.endRequest('/')
        self.assertIs(getattr(request, 'oops', None), None)
        self.assertEqual(self.getAddedResponse(request), '')
        log = self.getMemoryLog()
        self.assertEqual(len(log), 1)
        (timestamp, page_id, oops_id, duration, start_vss, start_rss,
         end_vss, end_rss) = log[0].split()
        self.assertEqual(page_id, 'Unknown')
        self.assertEqual(oops_id, '-')
        self.assertEqual(float(duration), 0.5)
        self.assertEqual(self.getProfilePaths(), [])
        self.assertCleanProfilerState()

    def test_memory_profile_with_non_defaults(self):
        "Does the memory profile work with an oops and pageid?"
        self.pushProfilingConfig(
            profiling_allowed='True',
            memory_profile_log=self.memory_profile_log)
        request = self.endRequest('/++profile++show/no-such-file',
                                  KeyError(), pageid='Foo')
        log = self.getMemoryLog()
        (timestamp, page_id, oops_id, duration, start_vss, start_rss,
         end_vss, end_rss) = log[0].split()
        self.assertEqual(page_id, 'Foo')
        self.assertEqual(oops_id, request.oopsid)
        self.assertCleanProfilerState()

    def test_combo_memory_and_profile(self):
        self.pushProfilingConfig(
            profiling_allowed='True',
            memory_profile_log=self.memory_profile_log)
        request = self.endRequest('/++profile++show/')
        self.assertIsInstance(request.oops, ErrorReport)
        self.assertIn('Top Inline Time', self.getAddedResponse(request))
        self.assertEqual(len(self.getMemoryLog()), 1)
        self.assertEqual(self.getProfilePaths(), [])
        self.assertCleanProfilerState()

    def test_profiling_oops_is_informational(self):
        self.pushProfilingConfig(profiling_allowed='True')
        request = self.endRequest('/++profile++show/')
        response = self.getAddedResponse(request)
        self.assertIsInstance(request.oops, ErrorReport)
        self.assertTrue(request.oops.informational)
        self.assertEquals(request.oops.type, 'ProfilingOops')
        self.assertCleanProfilerState()

    def test_real_oops_trumps_profiling_oops(self):
        self.pushProfilingConfig(profiling_allowed='True')
        request = self.endRequest('/++profile++show/no-such-file',
                                  KeyError('foo'))
        self.assertIsInstance(request.oops, ErrorReport)
        self.assertFalse(request.oops.informational)
        self.assertEquals(request.oops.type, 'KeyError')
        response = self.getAddedResponse(request)
        self.assertIn('Exception-Type: KeyError', response)
        self.assertCleanProfilerState()

    def test_oopsid_is_in_profile_filename(self):
        self.pushProfilingConfig(profiling_allowed='True')
        request = self.endRequest('/++profile++log/')
        self.assertIn("-" + request.oopsid + "-", self.getProfilePaths()[0])
        self.assertCleanProfilerState()


class TestBeforeTraverseHandler(TestCleanupProfiler):

    layer = layers.DatabaseFunctionalLayer

    def test_can_enable_profiling_over_config(self):
        # The flag profiling.enabled wins over a config that has
        # disabled profiling. This permits the use of profiling on qastaging
        # and similar systems.
        self.pushProfilingConfig(
            profiling_allowed='False', profile_all_requests='True',
            memory_profile_log='.')
        event = BeforeTraverseEvent(None,
            self._get_request('/++profile++show,log'))
        with FeatureFixture({'profiling.enabled':'on'}):
            profile.before_traverse(event)
            self.assertTrue(profile._profilers.profiling)
            self.assertIsInstance(profile._profilers.profiler, BzrProfiler)
            self.assertEquals(profile._profilers.actions, set(('show', 'log')))
