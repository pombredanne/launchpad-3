from canonical.ftests.pgsql import PgTestCase
from canonical.functional import FunctionalTestSetup

class LaunchpadTestCase(PgTestCase):
    """Test harness for Launchpad tests.

    Builds a fresh instance of the database for each test

    """

    dbname = 'launchpad_ftest'
    template = 'launchpad_ftest_template'

class LaunchpadFunctionalTestCase(LaunchpadTestCase):
    """Launchpad harness for Launchpad functional tests
    
    Just like LaunchpadTestCase, but bootstraps the Z3 machinery
    so Utilities, Adapters etc. are all available.

    """

    def setUp(self):
        super(LaunchpadFunctionalTestCase, self).setUp()
        FunctionalTestSetup().setUp()

    def tearDown(self):
        FunctionalTestSetup().tearDown()
        super(LaunchpadFunctionalTestCase, self).tearDown()

