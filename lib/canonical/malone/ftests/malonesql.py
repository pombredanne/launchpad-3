import unittest
from canonical.tests.functional import BrowserTestCase
from canonical.tests.pgsql import LaunchpadSchemaTestCase

class MaloneSQLTestCase(BrowserTestCase, LaunchpadSchemaTestCase):
    def setUp(self):
        LaunchpadSchemaTestCase.setUp(self)
        BrowserTestCase.setUp(self)

    def tearDown(self):
        BrowserTestCase.tearDown(self)
        LaunchpadSchemaTestCase.tearDown(self)

