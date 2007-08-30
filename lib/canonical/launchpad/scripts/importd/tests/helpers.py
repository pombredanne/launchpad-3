# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helpers for canonical.launchpad.scripts.importd tests."""

__metaclass__ = type

__all__ = [
    'ImportdTestCase', 'instrument_method', 'InstrumentedMethodObserver']


import os

from bzrlib.tests import TestCaseWithTransport

from canonical.config import config
from canonical.testing import LaunchpadZopelessLayer
from importd.tests.helpers import SandboxHelper
from importd.tests.test_bzrmanager import ProductSeriesHelper


class ImportdTestCase(TestCaseWithTransport):
    """Common base for test cases of importd script backends."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        TestCaseWithTransport.setUp(self)
        LaunchpadZopelessLayer.switchDbUser(config.importd.dbuser)
        self.bzrworking = 'bzrworking'
        self.sandbox = SandboxHelper()
        self.sandbox.setUp()
        self.bzrmirrors = self.sandbox.join('bzr-mirrors')
        os.mkdir(self.bzrmirrors)
        self.series_helper = ProductSeriesHelper()
        self.series_helper.setUp()
        self.series_helper.setUpSeries()
        self.series_id = self.series_helper.series.id

    def tearDown(self):
        self.series_helper.tearDown()
        self.sandbox.tearDown()
        TestCaseWithTransport.tearDown(self)

    def setUpOneCommit(self):
        workingtree = self.make_branch_and_tree(self.bzrworking)
        workingtree.commit('first commit')

    def mirrorPath(self):
        series = self.series_helper.getSeries()
        assert series.import_branch is not None
        branch_id = series.import_branch.id
        return os.path.join(self.bzrmirrors, '%08x' % branch_id)


def instrument_method(observer, obj, name):
    """Wrap the named method of obj in an InstrumentedMethod object.

    The InstrumentedMethod object will send events to the provided observer.
    """
    func = getattr(obj, name)
    instrumented_func = _InstrumentedMethod(observer, name, func)
    setattr(obj, name, instrumented_func)


class _InstrumentedMethod:
    """Wrapper for a callable, that sends event to an observer."""

    def __init__(self, observer, name, func):
        self.observer = observer
        self.name = name
        self.callable = func

    def __call__(self, *args, **kwargs):
        self.observer.called(self.name, args, kwargs)
        try:
            value = self.callable(*args, **kwargs)
        except Exception, exc:
            self.observer.raised(self.name, exc)
            raise
        else:
            self.observer.returned(self.name, value)
            return value


class InstrumentedMethodObserver:
    """Observer for InstrumentedMethod."""

    def __init__(self, called=None, returned=None, raised=None):
        if called is not None:
            self.called = called
        if returned is not None:
            self.returned = returned
        if raised is not None:
            self.raised = raised

    def called(self, name, args, kwargs):
        """Called before an instrumented method."""
        pass

    def returned(self, name, value):
        """Called after an instrumented method returned."""
        pass

    def raised(self, name, exc):
        """Called when an instrumented method raises."""
        pass
