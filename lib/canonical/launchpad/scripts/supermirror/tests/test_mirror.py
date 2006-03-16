import unittest

from canonical.launchpad.scripts.supermirror import mirror
from canonical.launchpad.scripts.supermirror.jobmanager import LockError


class TestMirrorCommand(unittest.TestCase):

    def testmirror(self):
        self.startMirror()

    def testMainCatchesDoublelock(self):
        manager = MockJobManager()
        manager.unlock()
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
        self.assertEquals(6, len(call_log))
        self.assertEquals(call_log[0], "__init__")
        self.assertEquals(call_log[1], "lock")
        self.assertEquals(call_log[2], "install")
        self.assertEquals(call_log[3], "run")
        self.assertEquals(call_log[4], "uninstall")
        self.assertEquals(call_log[5], "unlock")

    def startMirror(self):
        branches = []
        self.assertEqual(0, mirror(branches, managerClass=MockJobManager))


class TestMockJobManager(unittest.TestCase):

    def testCountsInstances(self):
        count = len(MockJobManager.instances)
        myothermanager = MockJobManager()
        self.assertEquals(count+1, len(MockJobManager.instances))

    def testCallsAreLogged(self):
        # FIXME: we need to check for return of something for some of these,
        # maybe
        manager = MockJobManager()
        manager.install()
        manager.lock()
        manager.unlock()
        manager.uninstall()
        # we want a list of tuples, one tuple for each api called.
        self.assertEquals(
            manager._call_log, 
            ["__init__", "install", "lock", "unlock", "uninstall"])


class MockJobManager:
    instances = []
    locked = False

    def __init__(self):
        MockJobManager.instances.append(self)
        self._call_log = []
        self._call_log.append("__init__")

    def add(self, item):
        pass

    def install(self):
        self._call_log.append("install")

    def lock(self, lockfilename=None):
        if MockJobManager.locked:
            raise LockError
        MockJobManager.locked = True
        self._call_log.append("lock")

    def unlock(self):
        MockJobManager.locked = False
        self._call_log.append("unlock")

    def run(self):
        self._call_log.append("run")

    def uninstall(self):
        self._call_log.append("uninstall")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
