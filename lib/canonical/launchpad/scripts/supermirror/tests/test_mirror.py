import unittest
from StringIO import StringIO

from canonical.launchpad.scripts.supermirror import mirror
from canonical.launchpad.scripts.supermirror.jobmanager import LockError


def setupFakeurllib():
    fakeurllib = MockUrlOpener()
    response = "first post\n"
    fakeurllib.set_response(response)
    return fakeurllib


class MockUrlOpener:

    def set_response(self, response):
        self.response = response

    def urlopen(self, url):
        return StringIO(self.response)
 

class TestMirrorCommand(unittest.TestCase):

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
        self.assertEquals(5, len(call_log))
        self.assertEquals(call_log[0], ("__init__",))
        self.assertEquals(call_log[1], ("lock",))
        self.assertEquals(call_log[2],
                          ("branchStreamToBranchList", "first post\n"))
        self.assertEquals(call_log[3], ("run",))
        self.assertEquals(call_log[4], ("unlock",))

    def startMirror(self):
        fakeurllib = setupFakeurllib()
        self.assertEqual(0, mirror(managerClass=MockJobManager,
                                   urllibOpener=fakeurllib.urlopen))


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
        manager.branchStreamToBranchList(StringIO("1 2"))
        manager.unlock()
        # we want a list of tuples, one tuple for each api called.
        self.assertEquals(
            manager._call_log, 
            [("__init__",), ("lock",), ("branchStreamToBranchList", "1 2"),
             ("unlock",)])


class MockJobManager:
    instances = []
    locked = False

    def __init__(self):
        MockJobManager.instances.append(self)
        self._call_log = []
        self._call_log.append(("__init__",))

    def add(self, item):
        pass

    def lock(self, lockfilename=None):
        if MockJobManager.locked:
            raise LockError(lockfilename)
        MockJobManager.locked = True
        self._call_log.append(("lock",))

    def branchStreamToBranchList(self, arg, client=None):
        self._call_log.append(("branchStreamToBranchList", arg.getvalue()))
        return [FakeMirrorRequest()]

    def unlock(self):
        MockJobManager.locked = False
        self._call_log.append(("unlock",))

    def run(self):
        self._call_log.append(("run",))


class FakeMirrorRequest(object):
    """A fake mirror request.

    This allows the mirror() call to have a branch to add which lets us
    test that it does indeed call manager.add().
    """

    def mirror():
        pass


class TestMockurllib(unittest.TestCase):
    def test_urlopen(self):
        fake_opener = MockUrlOpener()
        response = "first post\n"
        fake_opener.set_response(response)
        urldata = fake_opener.urlopen("http://slashdot.org")
        data = urldata.readlines()
        self.assertEquals(data, [response])
 

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
