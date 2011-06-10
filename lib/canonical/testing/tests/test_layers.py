# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for test layers."""

__metaclass__ = type
__all__ = []

import threading

from canonical.testing.layers import (
    BaseLayer,
    BaseWindmillLayer,
    DatabaseLayer,
    )
from lp.testing import TestCase


class TestBaseWindmillLayer(TestCase):

    layer_to_test = BaseWindmillLayer

    def test_db_reset_between_tests(self):
        # The db is reset between tests when DatabaseLayer layer's
        # testSetUp is called, if _reset_between_tests is True.
        self.assertTrue(
            issubclass(self.layer_to_test, DatabaseLayer))
        self.assertTrue(self.layer_to_test._reset_between_tests)


class TestThreadWaiting(TestCase):
    layer = BaseLayer

    def test_slow_thread(self):
        # BaseLayer waits a few seconds for threads spawned by the test
        # to shutdown. Test this is working by creating a thread that
        # will shut itself down in 0.5 seconds time.
        t = threading.Timer(0.5, lambda: None)
        t.start()

    def test_disabled_thread_check(self):
        # Confirm the BaseLayer.disable_thread_check code path works.
        BaseLayer.disable_thread_check = True
