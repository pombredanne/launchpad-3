# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.security.proxy import removeSecurityProxy
from canonical.testing.layers import ZopelessDatabaseLayer
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.soyuz.scripts.processaccepted import (
    close_bugs_for_sourcepackagerelease,
    )
from lp.testing import TestCaseWithFactory


class TestClosingBugs(TestCaseWithFactory):
    """Test the various bug closing methods in processaccepted.py.

    Tests are currently spread around the codebase; this is an attempt to
    start a unification in a single file and those other tests need
    migrating here.
    See also:
        * lp/soyuz/scripts/tests/test_queue.py
        * lib/lp/soyuz/doc/closing-bugs-from-changelogs.txt
        * lib/lp/archiveuploader/tests/nascentupload-closing-bugs.txt
    """
    layer = ZopelessDatabaseLayer

    def test_close_bugs_for_sourcepackagerelease_with_no_changes_file(self):
        # If there's no changes file it should read the changelog_entry on
        # the sourcepackagerelease.

        spr = self.factory.makeSourcePackageRelease()

        # Make 4 bugs and corresponding bugtasks and put them in an array
        # as tuples.
        bugs = []
        for i in range(4):
            bug = self.factory.makeBug()
            bugtask = self.factory.makeBugTask(
                target=spr.sourcepackage, bug=bug)
            bugs.append((bug, bugtask))

        # Make a changelog_entry for a package which contains the IDs of
        # the 4 bugs.
        changelog_entry="""
            closes: %s %s
            lp: %s %s
            """ % (
            bugs[0][0].id,
            bugs[1][0].id,
            bugs[2][0].id,
            bugs[3][0].id,
            )

        removeSecurityProxy(spr).changelog_entry = changelog_entry

        # Call the method and test it's closed the bugs.
        close_bugs_for_sourcepackagerelease(spr, changesfile_object=None)
        for bug, bugtask in bugs:
            self.assertEqual(bugtask.status, BugTaskStatus.FIXRELEASED)
