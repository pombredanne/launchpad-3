import unittest
from canonical.launchpad.scripts.ftpmaster import PubSourceChecker


class TestPubSourceChecker(unittest.TestCase):

    def setUp(self):
        """Initialize useful constant values."""
        self.name = 'foo'
        self.version = '1.0'
        self.component = 'main'
        self.section = 'python'
        self.urgency = 'URGENT'

    def test_initialization(self):
        """Check PubSourceChecker class initialization."""
        checker = PubSourceChecker(self.name, self.version, self.component,
                                   self.section, self.urgency)
        self.assertEqual(self.name, checker.name)
        self.assertEqual(self.version, checker.version)
        self.assertEqual(self.component, checker.component)
        self.assertEqual(self.section, checker.section)
        self.assertEqual(self.urgency, checker.urgency)
        self.assertEqual(0, len(checker.binaries))

    def test_single_binary_ok(self):
        """Probe single correct binary addition."""
        checker = PubSourceChecker(self.name, self.version, self.component,
                                   self.section, self.urgency)

        checker.addBinary('foo-dev', self.version, 'i386', self.component,
                          self.section, 'REQUIRED')

        checker.check()

        self.assertEqual(
            1, len(checker.binaries_details.components['foo-dev']))
        self.assertEqual(
            1, len(checker.binaries_details.sections['foo-dev']))
        self.assertEqual(
            1, len(checker.binaries_details.priorities['foo-dev']))

        self.assertEqual(None, checker.renderReport())

    def test_multi_binary_component_failure(self):
        """Probe multi binary with wrong component."""
        checker = PubSourceChecker(self.name, self.version, self.component,
                                   self.section, self.urgency)
        checker.addBinary('foo-dev', self.version, 'i386', 'universe',
                          self.section, 'REQUIRED')
        checker.addBinary('foo-dev', self.version, 'amd64', 'multiverse',
                          self.section, 'REQUIRED')

        checker.check()

        self.assertEqual(
            "foo_1.0 main/python/URGENT | 2 bin\n\t"
            "foo-dev_1.0 amd64 multiverse/python/REQUIRED\n\t\t"
            "W: Component mismatch: multiverse != universe",
            checker.renderReport())


    def test_multi_binary_priority_failure(self):
        """Probe multiple binaries with priority conflict."""
        checker = PubSourceChecker(self.name, self.version, self.component,
                                   self.section, self.urgency)
        checker.addBinary('foo-dev', self.version, 'i386', self.component,
                          self.section, 'REQUIRED')
        checker.addBinary('foo-dbg', self.version, 'i386', self.component,
                          self.section, 'EXTRA')
        checker.addBinary('foo-dev', self.version, 'amd64', self.component,
                          self.section, 'EXTRA')

        checker.check()

        self.assertEqual(
            "foo_1.0 main/python/URGENT | 3 bin\n"
            "\tfoo-dev_1.0 amd64 main/python/EXTRA\n"
            "\t\tW: Priority mismatch: EXTRA != REQUIRED",
            checker.renderReport())

def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestPubSourceChecker))
    return suite

def main(argv):
    suite = test_suite()
    runner = unittest.TextTestRunner(verbosity = 2)
    if not runner.run(suite).wasSuccessful():
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
