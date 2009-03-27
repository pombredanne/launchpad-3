# Copyright Canonical Limited, 2009, all rights reserved.

__metaclass__ = type

from canonical.lazr.interfaces.rest import IWebServiceConfiguration
from zope.component import getGlobalSiteManager, provideUtility
from zope.interface import implements
import unittest

class DummyWebServiceConfiguration:
    """A totally vanilla web service configuration."""
    implements(IWebServiceConfiguration)
    path_override = "api"
    service_version_uri_prefix = "beta"


class DummyConfigurationTestCase(unittest.TestCase):
    """A test case that installs a DummyWebServiceConfiguration."""

    def setUp(self):
        self.config = DummyWebServiceConfiguration()
        provideUtility(self.config, IWebServiceConfiguration)

    def tearDown(self):
        getGlobalSiteManager().unregisterUtility(
            self.config, IWebServiceConfiguration)

