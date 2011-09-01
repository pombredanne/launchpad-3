# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for hwdbsubmissions script."""

__metaclass__ = type

from canonical.testing.layers import ZopelessDatabaseLayer
from lp.hardwaredb.scripts.hwdbsubmissions import (
    ProcessingLoopForPendingSubmissions,
    ProcessingLoopForReprocessingBadSubmissions,
    )
from lp.testing import TestCaseWithFactory


class TestProcessingLoops(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer
