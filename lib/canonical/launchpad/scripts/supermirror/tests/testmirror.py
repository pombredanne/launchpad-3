import unittest
from supermirror.mirror import main
from StringIO import StringIO
from configuration import config


def setupFakeurllib():
    fakeurllib = MockUrlOpener()
    response = "first post\n"
    fakeurllib.set_response(response)
    return fakeurllib


class TestMirrorCommand(unittest.TestCase):
    def testmirror(self):
        self.startmain()
    def testMainCatchesDoublelock(self):
        manager = MockJobManager()
        manager.lock()
        try:
            self.startmain()
        finally:
            manager.unlock()

    def testMainMakesManager(self):
        count=len(MockJobManager.instances)
        self.startmain()
        self.assertEquals(count+1, len(MockJobManager.instances))

    def testMainRunsManager(self):
        self.startmain()
        call_log = MockJobManager.instances[-1]._call_log
        self.assertEquals(7, len(call_log))
        self.assertEquals(call_log[0], ("__init__",))
        self.assertEquals(call_log[1], ("lock",))
        self.assertEquals(call_log[2], ("install",))
        self.assertEquals(call_log[3],
                          ("branchStreamToBranchList", "first post\n"))
        self.assertEquals(call_log[4],
                          ("run",))
        self.assertEquals(call_log[5], ("uninstall",))
        self.assertEquals(call_log[6], ("unlock",))

    def startmain(self):
        fakeurllib = setupFakeurllib()
        self.assertEqual(0, main(['filename'], managerClass=MockJobManager,
                         urllibOpener=fakeurllib.urlopen))

class TestMockurllib(unittest.TestCase):
    def test_urlopen(self):
        fake_opener = MockUrlOpener()
        response = "first post\n"
        fake_opener.set_response(response)
        urldata = fake_opener.urlopen("http://slashdot.org")
        data = urldata.readlines()
        self.assertEquals(data, [response])

class TestMockJobManager(unittest.TestCase):
    def testCountsInstances(self):
        count=len(MockJobManager.instances)
        myothermanager=MockJobManager()
        self.assertEquals(count+1, len(MockJobManager.instances))

    def testCallsAreLogged(self):
        # FIXME: we need to check for return of something for some of these,
        # maybe
        manager = MockJobManager()
        manager.install()
        manager.lock()
        manager.branchStreamToBranchList(StringIO("kill"))
        manager.unlock()
        manager.uninstall()
        # we want a list of tuples, one tuple for each api called.
        self.assertEquals(manager._call_log, [("__init__",),
                                              ("install",),
                                              ("lock",),
                                              ("branchStreamToBranchList",
                                               "kill"),
                                              ("unlock",),
                                              ("uninstall",)])

class MockUrlOpener:
    def set_response(self, response):
        self.response = response
    def urlopen(self, url):
        return StringIO(self.response)

class MockJobManager:
    instances=[]
    locked = False

    def __init__(self):
        MockJobManager.instances.append(self)
        self._call_log = []
        self._call_log.append(("__init__",))

    def install(self):
        self._call_log.append(("install",))

    def lock(self):
        if MockJobManager.locked:
            raise LockError
        MockJobManager.locked = True
        self._call_log.append(("lock",))

    def branchStreamToBranchList(self, arg):
        self._call_log.append(("branchStreamToBranchList", arg.getvalue()))

    def unlock(self):
        MockJobManager.locked = False
        self._call_log.append(("unlock",))

    def run(self):
        self._call_log.append(("run",))

    def uninstall(self):
        self._call_log.append(("uninstall",))


class JobManagerError(StandardError):
    def __str__(self):
        return 'Unknown Jobmanager error: %s' \
                % (self.__class__.__name__, str(e))

class LockError(JobManagerError):
    def __str__(self):
        return 'Jobmanager unable to get master lock'

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

