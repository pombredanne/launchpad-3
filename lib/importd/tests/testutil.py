#!/usr/bin/python2.4
 
import sys
import logging
import unittest


class RevisionFactory:
    import CVS
    import os
    config = CVS.Config()
    Revision=CVS.Revision
    def create(self, filename, type,revision,log,time, predecessor=None):
        revA = self.CVS.WIPRevision()
        revA.filename = filename
        revA._type = type
        revA.revision = revision
        revA.revision_as_list = revA.make_rev_list(revision)
        revA.log = log
        revA.time = time
        revA.addcount = 5
        revA.delcount = 0
        revA.branch = "MAIN"
        if predecessor:
            revA._predecessor=predecessor
        return revA


class SilentLogHandler(logging.Handler):

    def emit(self, record):
        unused = record
        pass


def makeSilentLogger():
    """Create a logger that prints nothing."""
    logger = logging.Logger("collector")
    handler = SilentLogHandler()
    logger.addHandler(handler)
    return logger


class CollectingLogHandler(logging.Handler):
    """Logging handlers that saves logging messages."""

    def emit(self, record):
        message = record.getMessage()
        self.logger.messages.append(message)


def makeCollectingLogger():
    """Create a logger that saves its logging records to a list.

    The logging messages are saved in the 'messages' attribute of the returned
    logger object.
    """
    logger = logging.Logger('collector')
    logger.messages = []
    handler = CollectingLogHandler(logger)
    handler.logger = logger
    logger.addHandler(handler)
    return logger


class TestSuite(unittest.TestSuite):
    """I am an extended TestSuite with a visitor interface.
    This is primarily to allow filtering of tests - and suites or
    more in the future. An iterator of just tests wouldn't scale..."""

    def visit(self, visitor):
        """visit the composite. Visiting is depth-first.
        current callbacks are visitSuite and visitCase."""
        visitor.visitSuite(self)
        for test in self._tests:
            #Abusing types to avoid monkey patching unittest.TestCase. 
            # Maybe that would be better?
            try:
                test.visit(visitor)
            except AttributeError:
                if isinstance(test, unittest.TestCase):
                    visitor.visitCase(test)
                else:
                    print "unvisitable non-unittest.TestCase element %r" % test


class TestVisitor(object):
    """A visitor for Tests"""
    def visitSuite(self, aTestSuite):
        pass
    def visitCase(self, aTestCase):
        pass


class TestLoader(unittest.TestLoader):
    suiteClass = TestSuite


def main(**kwargs):
    unittest.main(testLoader=TestLoader(), **kwargs)

def register(name):
    def test_suite():
        return TestLoader().loadTestsFromModule(sys.modules[name])
    module = sys.modules[name]
    module.test_suite = test_suite
    if name == "__main__":
        main()


# arch-tag: b24269e1-a0bc-4024-9200-8af68ec76c02
