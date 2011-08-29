# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from textwrap import dedent
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import LaunchpadZopelessLayer
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
    layer = LaunchpadZopelessLayer

    def test_close_bugs_for_sourcepackagerelease_with_no_changes_file(self):
        # If there's no changes file it should read the changelog_entry on
        # the sourcepackagerelease.

        spr = self.factory.makeSourcePackageRelease(changelog_entry="blah")

        # Make 4 bugs and corresponding bugtasks and put them in an array
        # as tuples.
        bugs = []
        for i in range(5):
            bug = self.factory.makeBug()
            bugtask = self.factory.makeBugTask(
                target=spr.sourcepackage, bug=bug)
            bugs.append((bug, bugtask))

        unfixed_bug = self.factory.makeBug()
        unfixed_task = self.factory.makeBugTask(
            target=spr.sourcepackage, bug=unfixed_bug)

        # Make a changelog entry for a package which contains the IDs of
        # the 5 bugs separated across 2 releases.
        changelog=dedent("""
            foo (1.0-3) unstable; urgency=low

              * closes: %s, %s
              * lp: #%s, #%s

             -- Foo Bar <foo@example.com>  Tue, 01 Jan 1970 01:50:41 +0000

            foo (1.0-2) unstable; urgency=low

              * closes: %s

             -- Foo Bar <foo@example.com>  Tue, 01 Jan 1970 01:50:41 +0000

            foo (1.0-1) unstable; urgency=low

              * closes: %s

             -- Foo Bar <foo@example.com>  Tue, 01 Jan 1970 01:50:41 +0000

            """ % (
            bugs[0][0].id,
            bugs[1][0].id,
            bugs[2][0].id,
            bugs[3][0].id,
            bugs[4][0].id,
            unfixed_bug.id,
            ))
        lfa = self.factory.makeLibraryFileAlias(content=changelog)

        removeSecurityProxy(spr).changelog = lfa
        self.layer.txn.commit()

        # Call the method and test it's closed the bugs.
        close_bugs_for_sourcepackagerelease(spr, changesfile_object=None,
                                            since_version="1.0-1")
        for bug, bugtask in bugs:
            self.assertEqual(BugTaskStatus.FIXRELEASED, bugtask.status)

        self.assertEqual(BugTaskStatus.NEW, unfixed_task.status)

