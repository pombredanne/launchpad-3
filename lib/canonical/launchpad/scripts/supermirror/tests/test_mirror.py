import logging
import unittest

from canonical.launchpad.scripts.supermirror import mirror
from canonical.launchpad.scripts.supermirror.jobmanager import LockError
from canonical.testing import reset_logging


class TestMirrorCommand(unittest.TestCase):

    def setUp(self):
        # We set the log level to CRITICAL so that the log messages
        # are suppressed.
        logging.basicConfig(level=logging.CRITICAL)
        self.logger = logging.getLogger()

    def tearDown(self):
        reset_logging()

    def testmirror(self):
        self.startMirror()

    def testMainCatchesDoublelock(self):
        manager = MockJobManager()
        manager.lock()
        try:
            self.startMirror()
        finally:
            manager.unlock()

    def testMainMakesManager(self):
        count = len(MockJobManager.instances)
        self.startMirror()
        self.assertEquals(count+1, len(MockJobManager.instances))

    def testMainRunsManager(self):
        self.startMirror()
        call_log = MockJobManager.instances[-1]._call_log
        self.assertEquals(
            call_log, [
                ("__init__",),
                ("lock",),
                ("run", self.logger),
                ("activity",),
                ("unlock",)])

    def startMirror(self):
        self.assertEqual(0, mirror(self.logger, MockJobManager()))


class TestMockJobManager(unittest.TestCase):

    def testCountsInstances(self):
        count = len(MockJobManager.instances)
        myothermanager = MockJobManager()
        self.assertEquals(count+1, len(MockJobManager.instances))

    def testCallsAreLogged(self):
        # FIXME: we need to check for return of something for some of these,
        # maybe
        manager = MockJobManager()
        manager.lock()
        manager.unlock()
        # we want a list of tuples, one tuple for each api called.
        self.assertEquals(
            manager._call_log,
            [("__init__",), ("lock",), ("unlock",)])


class MockJobManager:
    instances = []
    locked = False

    def __init__(self):
        MockJobManager.instances.append(self)
        self._call_log = []
        self._call_log.append(("__init__",))

    def lock(self, lockfilename=None):
        if MockJobManager.locked:
            raise LockError(lockfilename)
        MockJobManager.locked = True
        self._call_log.append(("lock",))

    def unlock(self):
        MockJobManager.locked = False
        self._call_log.append(("unlock",))

    def run(self, logger):
        self._call_log.append(("run", logger))

    def recordActivity(self, started, completed):
        self._call_log.append(("activity",))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
