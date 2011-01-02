# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from doctest import (
    DocTestSuite,
    ELLIPSIS,
    )

from canonical.launchpad.webapp import publisher


def test_suite():
    suite = DocTestSuite(publisher, optionflags=ELLIPSIS)
    return suite
