# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run doctests."""

__metaclass__ = type

import os.path
from textwrap import dedent

import zope.pagetemplate.engine
from zope.pagetemplate.pagetemplate import PageTemplate
from zope.publisher.browser import TestRequest

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import (
    LaunchpadFunctionalLayer,
    MemcachedLayer,
    )
from lp.services.testing import build_test_suite


here = os.path.dirname(os.path.realpath(__file__))


class TestPageTemplate(PageTemplate):
    """A cutdown PageTemplate implementation suitable for our tests."""

    _num_instances = 0

    def __init__(self, source):
        super(TestPageTemplate, self).__init__()
        TestPageTemplate._num_instances += 1
        self._my_instance_num = TestPageTemplate._num_instances
        self.pt_edit(source, 'text/html')

    def pt_source_file(self):
        return 'fake/test_%d.pt' % self._my_instance_num

    def pt_getEngine(self):
        # The <tales:expressiontype> ZCML only registers with this
        # engine, not the default.
        return zope.pagetemplate.engine.Engine

    def pt_getContext(self, args=(), options={}):
        # Build a minimal context. The cache: expression requires
        # a request.
        context = dict(options)
        context.setdefault('request', TestRequest())
        return context


def memcacheSetUp(test):
    setUp(test)
    test.globs['TestPageTemplate'] = TestPageTemplate
    test.globs['dedent'] = dedent
    test.globs['MemcachedLayer'] = MemcachedLayer
    test.globs['LaunchpadTestRequest'] = LaunchpadTestRequest


def suite_for_doctest(filename):
    return LayeredDocFileSuite(
        '../doc/%s' % filename,
        setUp=memcacheSetUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer)

special = {
    'tales-cache.txt': suite_for_doctest('tales-cache.txt'),
    'restful-cache.txt': suite_for_doctest('restful-cache.txt'),
    }


def test_suite():
    return build_test_suite(here, special, layer=LaunchpadFunctionalLayer)
