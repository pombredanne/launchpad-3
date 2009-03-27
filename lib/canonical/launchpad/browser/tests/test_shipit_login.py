# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test harness for running the shipit-login.txt tests."""

__metaclass__ = type

__all__ = []

import unittest

from openid.fetchers import (
    getDefaultFetcher, setDefaultFetcher, Urllib2Fetcher)
from canonical.launchpad.testing.pages import setUpGlobs
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing.layers import AppServerLayer

orig_fetcher = None


def customSetUp(test):
    setUp(test)
    setUpGlobs(test)
    # Make sure python-openid uses Urllib2Fetcher in this test because
    # CurlHTTPFetcher may barf because of our self-signed certificates.
    orig_fetcher = getDefaultFetcher()
    setDefaultFetcher(Urllib2Fetcher())


def customTearDown(test):
    tearDown(test)
    setDefaultFetcher(orig_fetcher)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(LayeredDocFileSuite(
        'shipit-login.txt', setUp=customSetUp, tearDown=customTearDown,
        layer=AppServerLayer))
    return suite
