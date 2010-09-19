# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test the lpmoderate monekypatches"""

from __future__ import with_statement

__metaclass__ = type
__all__ = []

from canonical.testing import (
    FunctionalLayer,
    DatabaseFunctionalLayer,
    )
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class TestLPModerateTestCase(TestCaseWithFactory):
    """Test the installation of lpmoderate."""

    layer = FunctionalLayer

    def test_import(self):
        try:
            import Mailman.Handlers.LPModerate
        except:
            self.fail('monkeypatches/lpmoderate.py is not installed.')
