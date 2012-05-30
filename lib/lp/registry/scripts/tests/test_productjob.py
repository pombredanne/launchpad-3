# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Tests for the scripts productjob module."""

__metaclass__ = type

import logging

from lp.registry.scripts.productjob import ProductJobManager
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class ProductJobManagerTestCase(TestCaseWithFactory):
    # Test the ProductJobManager class.
    layer = DatabaseFunctionalLayer

    def test_init(self):
        logger = logging.getLogger('request-product-jobs')
        manager = ProductJobManager(logger)
        self.assertIs(logger, manager.logger)
