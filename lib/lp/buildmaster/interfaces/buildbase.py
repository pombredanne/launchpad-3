# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Common build interfaces."""

__metaclass__ = type

__all__ = ['IBuildBase']

from zope.interface import Attribute, Interface
from zope.schema import Choice, Datetime, Object, TextLine, Timedelta
from lazr.enum import DBEnumeratedType
from lazr.restful.declarations import exported

from lp.buildmaster.interfaces.builder import IBuilder
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad import _


class IBuildBase(Interface):
    """Common interface shared by farm jobs that build a package."""

    datecreated = exported(
        Datetime(
            title=_('Date created'), required=True, readonly=True,
            description=_("The time when the build request was created.")))

    # Really BuildStatus. Patched in _schema_circular_imports.
    buildstate = exported(
        Choice(
            title=_('State'), required=True, vocabulary=DBEnumeratedType,
            description=_("The current build state.")))

    date_first_dispatched = exported(
        Datetime(
            title=_('Date first dispatched'), required=False,
            description=_("The actual build start time. Set when the build "
                          "is dispatched the first time and not changed in "
                          "subsequent build attempts.")))

    builder = Object(
        title=_("Builder"), schema=IBuilder, required=False,
        description=_("The Builder which address this build request."))

    datebuilt = exported(
        Datetime(
            title=_('Date built'), required=False,
            description=_("The time when the build result got collected.")))

    buildduration = Timedelta(
        title=_("Build Duration"), required=False,
        description=_("Build duration interval, calculated when the "
                      "build result gets collected."))

    # XXX: jml 2010-01-12: Rename to build_log.
    buildlog = Object(
        schema=ILibraryFileAlias, required=False,
        title=_("The LibraryFileAlias containing the entire buildlog."))

    buildqueue_record = Attribute("Corresponding BuildQueue record")

    is_private = Attribute("Whether the build should be treated as private.")

    policy_name = Attribute(
        "The upload policy to use for handling these builds.")

    def getUploaderCommand():
        """Get the command to run as the uploader.

        :return: A list of command line arguments, beginning with the
            executable.
        """

    def handleStatus(status, librarian, slave_status):
        """Handle a finished build status from a slave.

        :param status: Slave build status string with 'BuildStatus.' stripped.
        :param slave_status: A dict as returned by IBuilder.slaveStatus
        """

    def getLogFromSlave():
        """Get last buildlog from slave.

        Invoke getFileFromSlave method with 'buildlog' identifier.
        """

    def storeBuildInfo(librarian, slave_status):
        """Store available information for the build job.

        Subclasses can override this as needed, and call it from custom status
        handlers, but it should not be called externally.
        """

    def notify(extra_info=None):
        """Notify current build state to related people via email."""
