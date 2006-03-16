import unittest
import signal

from canonical.launchpad.scripts.supermirror import jobmanager 

class TestJobManagerController(unittest.TestCase):

    def testExistance(self):
        from canonical.launchpad.scripts.supermirror.jobmanager import (
            JobManagerController)


class TestSignaling(unittest.TestCase):

    def handler(self, signal_number, stack_frame):
        self.caught = True

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.controller = jobmanager.JobManagerController()

    def testOrderKill(self):
        self.caught = False
        oldsignal = signal.signal(self.controller.killSignal, self.handler)
        try:
            self.controller.kill()
            self.assertEqual(True, self.caught)  
        finally:
            signal.signal(self.controller.killSignal, oldsignal)

    def testKillSignalIsSIGTERM(self):
        self.assertEqual(self.controller.killSignal, signal.SIGTERM)

    #FIXME: need test for sleep


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
