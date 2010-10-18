# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from doctest import DocTestSuite
import canonical.base

def test_suite():
    suite = DocTestSuite(canonical.base)
    return suite
