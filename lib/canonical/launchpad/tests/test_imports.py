# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite


def test_suite():
    return LayeredDocFileSuite('test_imports.txt')

