# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import doctest

from canonical.launchpad.testing.systemdocs import default_optionflags

def test_suite():
    return doctest.DocTestSuite(
        'canonical.zeca.ftests.harness', optionflags=default_optionflags)

