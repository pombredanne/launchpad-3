# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'DistroReleaseQueue',
    'DistroReleaseQueueBuild',
    'DistroReleaseQueueSource',
    'DistroReleaseQueueCustom',
    'DistroReleaseQueueSet',
    ]

import os
import tempfile
import pytz
from datetime import datetime
from warnings import warn

from zope.interface import implements

from sqlobject import (
    ForeignKey, MultipleJoin, StringCol, SQLObjectNotFound)

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW

from canonical.lp.dbschema import (
    EnumCol, DistroReleaseQueueStatus, DistroReleaseQueueCustomFormat,
    PackagePublishingPocket, PackagePublishingStatus)

from canonical.launchpad.interfaces import (
    IDistroReleaseQueue, IDistroReleaseQueueBuild, IDistroReleaseQueueSource,
    IDistroReleaseQueueCustom, NotFoundError, QueueStateWriteProtectedError,
    QueueInconsistentStateError, QueueSourceAcceptError,
    IDistroReleaseQueueSet)

from canonical.launchpad.database.publishing import (
    SecureSourcePackagePublishingHistory,
    SecureBinaryPackagePublishingHistory)

from canonical.cachedproperty import cachedproperty

# There are imports below in DistroReleaseQueueCustom for various bits
# of the archivepublisher which cause circular import errors if they
# are placed here.


def filechunks(file, chunk_size=256*1024):
    """Return an iterator which reads chunks of the given file."""
    # We use the two-arg form of the iterator here to form an iterator
    # which reads chunks from the given file.
    return iter(lambda: file.read(chunk_size), '')


def debug(logger, msg):
    """Shorthand debug notation for publish() methods."""
    if logger is not None:
        logger.debug(msg)


class DistroReleaseQueue(SQLBase):
    """A Queue item for Lucille."""
    implements(IDistroReleaseQueue)

    status = EnumCol(dbName='status', unique=False,
                     default=DistroReleaseQueueStatus.NEW,
                     schema=DistroReleaseQueueStatus)

    distrorelease = ForeignKey(dbName="distrorelease",
                               foreignKey='DistroRelease')

    pocket = EnumCol(dbName='pocket', unique=False, default=None, notNull=True,
                     schema=PackagePublishingPocket)

    changesfilealias = ForeignKey(dbName='changesfilealias',
                                  foreignKey="LibraryFileAlias",
                                  notNull=True)

    # Join this table to the DistroReleaseQueueBuild and the
    # DistroReleaseQueueSource objects which are related.
    sources = MultipleJoin('DistroReleaseQueueSource',
                           joinColumn='distroreleasequeue')
    builds = MultipleJoin('DistroReleaseQueueBuild',
                          joinColumn='distroreleasequeue')
    # Also the custom files associated with the build.
    customfiles = MultipleJoin('DistroReleaseQueueCustom',
                               joinColumn='distroreleasequeue')

    def _set_status(self, value):
        """Directly write on 'status' is forbidden.

        Force user to use the provided machine-state methods.
        Raises QueueStateWriteProtectedError.
        """
        # allow 'status' write only in creation process.
        if self._SO_creating:
            self._SO_set_status(value)
            return
        # been facist
        raise QueueStateWriteProtectedError(
            'Directly write on queue status is forbidden use the '
            'provided methods to set it.')

    def set_new(self):
        """See IDistroReleaseQueue."""
        self._SO_set_status(DistroReleaseQueueStatus.NEW)

    def set_unapproved(self):
        """See IDistroReleaseQueue."""
        self._SO_set_status(DistroReleaseQueueStatus.UNAPPROVED)

    def set_accepted(self):
        """See IDistroReleaseQueue."""
        for source in self.sources:
            # if something goes wrong we will raise an exception
            # (QueueSourceAcceptError) before setting any value.
            # Mask the error with state-machine default exception
            try:
                source.checkComponentAndSection()
            except QueueSourceAcceptError, info:
                raise QueueInconsistentStateError(info)
        # if the previous checks applied and pass we do set the value
        self._SO_set_status(DistroReleaseQueueStatus.ACCEPTED)

    def set_done(self):
        """See IDistroReleaseQueue."""
        self._SO_set_status(DistroReleaseQueueStatus.DONE)

    def set_rejected(self):
        """See IDistroReleaseQueue."""
        self._SO_set_status(DistroReleaseQueueStatus.REJECTED)

    @cachedproperty
    def changesfilename(self):
        """A changes filename to accurately represent this upload."""
        filename = self.sourcepackagename.name + "_" + self.sourceversion + "_"
        arch_done = False
        if len(self.sources):
            filename += "source"
            arch_done = True
        for build in self.builds:
            if arch_done:
                filename += "+"
            filename += build.build.distroarchrelease.architecturetag
            arch_done = True
        filename += ".changes"
        return filename

    @cachedproperty
    def datecreated(self):
        """The date on which this queue item was created.

        We look through the sources/builds of this queue item to find out
        when we created it. This is heuristic for now but may be made into
        a column at a later date.
        """
        # If we can find a source, return it
        for source in self.sources:
            return source.sourcepackagerelease.dateuploaded
        # Ditto for builds
        for build in self.builds:
            return build.build.datecreated
        # Strange, but there's no source or build, complain
        raise NotFoundError()

    @property
    def age(self):
        """See IDistroReleaseQueue"""
        UTC = pytz.timezone('UTC')
        now = datetime.now(UTC)
        return now - self.datecreated


    @cachedproperty
    def sourcepackagename(self):
        """The source package name related to this queue item.

        We look through sources/builds to find it. This is heuristic for now
        but may be made into a column at a later date.
        """
        # If there's a source, use it
        for source in self.sources:
            return source.sourcepackagerelease.sourcepackagename
        # ditto builds
        for build in self.builds:
            return build.sourcepackagerelease.sourcepackagename
        # strange, no source or build
        raise NotFoundError()

    @cachedproperty
    def sourceversion(self):
        """The source package version related to this queue item.

        This is currently heuristic but may be more easily calculated later.
        """
        # If there's a source, use it
        for source in self.sources:
            return source.sourcepackagerelease.version
        # ditto builds
        for build in self.builds:
            return build.sourcepackagerelease.version
        # strange, no source or build
        raise NotFoundError()

    def realiseUpload(self, logger=None):
        """See IDistroReleaseQueue."""
        assert self.status == DistroReleaseQueueStatus.ACCEPTED

        # In realising an upload we first load all the sources into
        # the publishing tables, then the binaries, then we attempt
        # to publish the custom objects.
        for source in self.sources:
            source.publish(logger)
        for build in self.builds:
            build.publish(logger)
        for customfile in self.customfiles:
            customfile.publish(logger)

        self.set_done()

    def addSource(self, spr):
        """See IDistroReleaseQueue."""
        return DistroReleaseQueueSource(distroreleasequeue=self.id,
                                        sourcepackagerelease=spr.id)

    def addBuild(self, build):
        """See IDistroReleaseQueue."""
        return DistroReleaseQueueBuild(distroreleasequeue=self.id,
                                       build=build.id)

    def addCustom(self, library_file, custom_type):
        """See IDistroReleaseQueue."""
        return DistroReleaseQueueCustom(distroreleasequeue=self.id,
                                        libraryfilealias=library_file.id,
                                        customformat=custom_type)


class DistroReleaseQueueBuild(SQLBase):
    """A Queue item's related builds (for Lucille)."""
    implements(IDistroReleaseQueueBuild)

    distroreleasequeue = ForeignKey(
        dbName='distroreleasequeue',
        foreignKey='DistroReleaseQueue'
        )

    build = ForeignKey(dbName='build', foreignKey='Build')

    def publish(self, logger=None):
        """See IDistroReleaseQueueBuild."""
        # Determine the build's architecturetag.
        build_archtag = self.build.distroarchrelease.architecturetag
        # Determine the target arch release.
        # This will raise NotFoundError if anything odd happens.
        target_dar = self.distroreleasequeue.distrorelease[build_archtag]
        debug(logger, "Publishing build to %s/%s/%s" % (
            target_dar.distrorelease.distribution.name,
            target_dar.distrorelease.name,
            build_archtag))
        # And get the other distroarchreleases
        other_dars = set(self.distroreleasequeue.distrorelease.architectures)
        other_dars = other_dars - set([target_dar])
        # First up, publish everything in this build into that dar.
        published_binaries = []
        for binary in self.build.binarypackages:
            target_dars = set([target_dar])
            if not binary.architecturespecific:
                target_dars = target_dars or other_dars
                debug(logger, "... %s/%s (Arch Independent)" % (
                    binary.binarypackagename.name,
                    binary.version))
            else:
                debug(logger, "... %s/%s (Arch Specific)" % (
                    binary.binarypackagename.name,
                    binary.version))
            for each_target_dar in target_dars:
                # XXX: dsilvers: 20051020: What do we do about embargoed
                # binaries here? bug 3408
                sbpph = SecureBinaryPackagePublishingHistory(
                    binarypackagerelease=binary.id,
                    distroarchrelease=each_target_dar.id,
                    component=binary.component.id,
                    section=binary.section.id,
                    priority=binary.priority,
                    status=PackagePublishingStatus.PENDING,
                    datecreated=UTC_NOW,
                    pocket=self.distroreleasequeue.pocket,
                    embargo=False
                    )
                published_binaries.append(sbpph)


class DistroReleaseQueueSource(SQLBase):
    """A Queue item's related sourcepackagereleases (for Lucille)."""
    implements(IDistroReleaseQueueSource)

    distroreleasequeue = ForeignKey(
        dbName='distroreleasequeue',
        foreignKey='DistroReleaseQueue'
        )

    sourcepackagerelease = ForeignKey(
        dbName='sourcepackagerelease',
        foreignKey='SourcePackageRelease'
        )

    def checkComponentAndSection(self):
        """See IDistroReleaseQueueSource."""
        distrorelease = self.distroreleasequeue.distrorelease
        component = self.sourcepackagerelease.component
        section = self.sourcepackagerelease.section

        if (component not in distrorelease.components):
            raise QueueSourceAcceptError(
                'Component "%s" is not allowed in %s' % (component.name,
                                                         distrorelease.name))

        if (section not in distrorelease.sections):
            raise QueueSourceAcceptError(
                'Section "%s" is not allowed in %s' % (section.name,
                                                       distrorelease.name))

    def publish(self, logger=None):
        """See IDistroReleaseQueueSource."""
        # Publish myself in the distrorelease pointed at by my queue item.
        # XXX: dsilvers: 20051020: What do we do here to support embargoed
        # sources? bug 3408
        debug(logger, "Publishing source %s/%s to %s/%s" % (
            self.sourcepackagerelease.sourcepackagename.name,
            self.sourcepackagerelease.version,
            self.distroreleasequeue.distrorelease.distribution.name,
            self.distroreleasequeue.distrorelease.name))

        return SecureSourcePackagePublishingHistory(
            distrorelease=self.distroreleasequeue.distrorelease.id,
            sourcepackagerelease=self.sourcepackagerelease.id,
            component=self.sourcepackagerelease.component.id,
            section=self.sourcepackagerelease.section.id,
            status=PackagePublishingStatus.PENDING,
            datecreated=UTC_NOW,
            pocket=self.distroreleasequeue.pocket,
            embargo=False)


class DistroReleaseQueueCustom(SQLBase):
    """A Queue item's related custom format uploads."""
    implements(IDistroReleaseQueueCustom)

    distroreleasequeue = ForeignKey(
        dbName='distroreleasequeue',
        foreignKey='DistroReleaseQueue'
        )

    customformat = EnumCol(dbName='customformat', unique=False,
                           default=None, notNull=True,
                           schema=DistroReleaseQueueCustomFormat)

    libraryfilealias = ForeignKey(dbName='libraryfilealias',
                                  foreignKey="LibraryFileAlias",
                                  notNull=True)

    def publish(self, logger=None):
        """See IDistroReleaseQueueCustom."""
        # This is a marker as per the comment in dbschema.py.
        ##CUSTOMFORMAT##
        # Essentially, if you alter anything to do with what custom formats
        # are, what their tags are, or anything along those lines, you should
        # grep for the marker in the source tree and fix it up in every place
        # so marked.
        name = "publish_" + self.customformat.name
        method = getattr(self, name, None)
        if method is not None:
            method(logger)
        else:
            raise NotFoundError("Unable to find a publisher method for %s" % (
                self.customformat.name))

    def publish_DEBIAN_INSTALLER(self, logger=None):
        """See IDistroReleaseQueueCustom."""
        # To process a DI tarball we need write the tarball out to a
        # temporary file, locate the archive, process the tarball, and
        # remove the temp file.

        # These imports are local to prevent loops in the importing
        from canonical.archivepublisher.debian_installer import (
            process_debian_installer)
        from canonical.archivepublisher.config import Config as ArchiveConfig

        temp_file_fd, temp_file_name = tempfile.mkstemp()
        temp_file = os.fdopen(temp_file_fd, "wb")
        # Pump the file from the librarian...
        self.libraryfilealias.open()
        for chunk in filechunks(self.libraryfilealias):
            temp_file.write(chunk)
        temp_file.close()
        self.libraryfilealias.close()
        # Find the archive root...
        dr = self.distroreleasequeue.distrorelease
        config = ArchiveConfig(dr.distribution, dr.distribution.releases)
        try:
            process_debian_installer(config.archive_root,
                                     temp_file_name,
                                     dr.name)
        finally:
            os.remove(temp_file_name)

    def publish_ROSETTA_TRANSLATIONS(self, logger=None):
        """See IDistroReleaseQueueCustom."""
        raise NotImplementedError()


class DistroReleaseQueueSet:
    """See IDistroReleaseQueueSet"""
    implements(IDistroReleaseQueueSet)

    def __iter__(self):
        """See IDistroReleaseQueueSet."""
        return iter(DistroReleaseQueue.select())

    def __getitem__(self, queue_id):
        """See IDistroReleaseQueueSet."""
        try:
            return DistroReleaseQueue.get(queue_id)
        except SQLObjectNotFound:
            raise NotFoundError(queue_id)

    def get(self, queue_id):
        """See IDistroReleaseQueueSet."""
        try:
            return DistroReleaseQueue.get(queue_id)
        except SQLObjectNotFound:
            raise NotFoundError(queue_id)

    def count(self, status=None):
        """See IDistroReleaseQueueSet."""
        clause = None
        if status:
            clause = "status=%s" % sqlvalues(status)

        return DistroReleaseQueue.select(clause).count()
