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
from lazr.restful.fields import Reference

from lp.buildmaster.interfaces.builder import IBuilder
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.archive import IArchive
from lp.soyuz.interfaces.buildqueue import IBuildQueue
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad import _


class IBuildBase(Interface):
    """Common interface shared by farm jobs that build a package."""

    # XXX: wgrant 2010-01-20 bug=507712: Most of these attribute names
    # are bad.
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

    buildlog = Object(
        schema=ILibraryFileAlias, required=False,
        title=_("The LibraryFileAlias containing the entire buildlog."))

    buildqueue_record = Object(
        schema=IBuildQueue, required=True,
        title=_("Corresponding BuildQueue record"))

    is_private = Attribute("Whether the build should be treated as private.")

    policy_name = TextLine(
        title=_("Policy name"), required=True,
        description=_("The upload policy to use for handling these builds."))

    archive = exported(
        Reference(
            title=_("Archive"), schema=IArchive,
            required=True, readonly=True,
            description=_("The Archive context for this build.")))

    current_component = Attribute(
        "Component where the source related to this build was last "
        "published.")

    pocket = exported(
        Choice(
            title=_('Pocket'), required=True,
            vocabulary=PackagePublishingPocket,
            description=_("The build targeted pocket.")))

    dependencies = exported(
        TextLine(
            title=_("Dependencies"), required=False,
            description=_("Debian-like dependency line that must be satisfied"
                          " before attempting to build this request.")))

    distribution = exported(
        Reference(
            schema=IDistribution,
            title=_("Distribution"), required=True,
            description=_("Shortcut for its distribution.")))

    def getUploaderCommand(upload_leaf):
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

    def queueBuild():
        """Create a BuildQueue entry for this build."""

    def estimateDuration():
        """Estimate the build duration."""

    def storeBuildInfo(librarian, slave_status):
        """Store available information for the build job.

        Subclasses can override this as needed, and call it from custom status
        handlers, but it should not be called externally.
        """

    def storeUploadLog(content):
        """Store the given content as the build upload_log.

        :param content: string containing the upload-processor log output for
            the binaries created in this build.
        """

    def notify(extra_info=None):
        """Notify current build state to related people via email."""

    def makeJob():
        """Construct and return an `IBuildFarmJob` for this build."""
