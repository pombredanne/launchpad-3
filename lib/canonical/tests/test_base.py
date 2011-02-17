# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from doctest import DocTestSuite
from lp.services.utils import base

def test_suite():
    suite = DocTestSuite(base.__doc__)
    return suite
