# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from doctest import DocTestSuite

from canonical.launchpad import datetimeutils


def test_suite():
    return DocTestSuite(datetimeutils)
