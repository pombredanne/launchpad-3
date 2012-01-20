# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""FTPMaster utilities."""

__metaclass__ = type

__all__ = ['PackageRemover']

from zope.component import getUtility

from lp.registry.interfaces.person import IPersonSet
from lp.services.browser_helpers import get_plural_text
from lp.soyuz.scripts.ftpmasterbase import (
    SoyuzScript,
    SoyuzScriptError,
    )


class PackageRemover(SoyuzScript):
    """SoyuzScript implementation for published package removal.."""

    usage = '%prog -s warty mozilla-firefox'
    description = 'REMOVE a published package.'
    success_message = (
        "The archive will be updated in the next publishing cycle.")

    def add_my_options(self):
        """Adding local options."""
        # XXX cprov 20071025: we need a hook for loading SoyuzScript default
        # options automatically. This is ugly.
        SoyuzScript.add_my_options(self)

        # Mode options.
        self.parser.add_option("-b", "--binary", dest="binaryonly",
                               default=False, action="store_true",
                               help="Remove binaries only.")
        self.parser.add_option("-S", "--source-only", dest="sourceonly",
                               default=False, action="store_true",
                               help="Remove source only.")

        # Removal information options.
        self.parser.add_option("-u", "--user", dest="user",
                               help="Launchpad user name.")
        self.parser.add_option("-m", "--removal_comment",
                               dest="removal_comment",
                               help="Removal comment")

    def mainTask(self):
        """Execute the package removal task.

        Build location and target objects.

        Can raise SoyuzScriptError.
        """
        if len(self.args) == 0:
            raise SoyuzScriptError(
                "At least one non-option argument must be given, "
                "a package name to be removed.")

        if self.options.user is None:
            raise SoyuzScriptError("Launchpad username must be given.")

        if self.options.removal_comment is None:
            raise SoyuzScriptError("Removal comment must be given.")

        removed_by = getUtility(IPersonSet).getByName(self.options.user)
        if removed_by is None:
            raise SoyuzScriptError(
                "Invalid launchpad username: %s" % self.options.user)

        removables = []
        for packagename in self.args:
            if self.options.binaryonly:
                removables.extend(
                    self.findLatestPublishedBinaries(packagename))
            elif self.options.sourceonly:
                removables.append(self.findLatestPublishedSource(packagename))
            else:
                source_pub = self.findLatestPublishedSource(packagename)
                removables.append(source_pub)
                removables.extend(source_pub.getPublishedBinaries())

        self.logger.info("Removing candidates:")
        for removable in removables:
            self.logger.info('\t%s', removable.displayname)

        self.logger.info("Removed-by: %s", removed_by.displayname)
        self.logger.info("Comment: %s", self.options.removal_comment)

        removals = []
        for removable in removables:
            removable.requestDeletion(
                removed_by=removed_by,
                removal_comment=self.options.removal_comment)
            removals.append(removable)

        if len(removals) == 0:
            self.logger.info("No package removed (bug ?!?).")
        else:
            self.logger.info(
                "%d %s successfully removed.", len(removals),
                get_plural_text(len(removals), "package", "packages"))

        # Information returned mainly for the benefit of the test harness.
        return removals
