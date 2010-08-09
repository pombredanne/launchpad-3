# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Common build base classes."""


from __future__ import with_statement

__metaclass__ = type

__all__ = [
    'BuildBase',
    ]

from cStringIO import StringIO

from storm.store import Store
from zope.component import getUtility

from canonical.launchpad.helpers import filenameToContentType
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.model.buildqueue import BuildQueue


class BuildBase:
    """A mixin class providing functionality for farm jobs that build a
    package.

    Note: this class does not implement IBuildBase as we currently duplicate
    the properties defined on IBuildBase on the inheriting class tables.
    BuildBase cannot therefore implement IBuildBase itself, as storm requires
    that the corresponding __storm_table__ be defined for the class. Instead,
    the classes using the BuildBase mixin must ensure that they implement
    IBuildBase.
    """
    policy_name = 'buildd'

    def _getProxiedFileURL(self, library_file):
        """Return the 'http_url' of a `ProxiedLibraryFileAlias`."""
        # Avoiding circular imports.
        from canonical.launchpad.browser.librarian import (
            ProxiedLibraryFileAlias)

        proxied_file = ProxiedLibraryFileAlias(library_file, self)
        return proxied_file.http_url

    @property
    def build_log_url(self):
        """See `IBuildBase`."""
        if self.buildlog is None:
            return None
        return self._getProxiedFileURL(self.buildlog)

    @property
    def upload_log_url(self):
        """See `IBuildBase`."""
        if self.upload_log is None:
            return None
        return self._getProxiedFileURL(self.upload_log)

    @staticmethod
    def _handleStatus_PACKAGEFAIL(build, librarian, slave_status, logger):
        """Handle a package that had failed to build.

        Build has failed when trying the work with the target package,
        set the job status as FAILEDTOBUILD, store available info and
        remove Buildqueue entry.
        """
        build.status = BuildStatus.FAILEDTOBUILD
        build.storeBuildInfo(build, librarian, slave_status)
        build.buildqueue_record.builder.cleanSlave()
        build.notify()
        build.buildqueue_record.destroySelf()

    @staticmethod
    def _handleStatus_DEPFAIL(build, librarian, slave_status, logger):
        """Handle a package that had missing dependencies.

        Build has failed by missing dependencies, set the job status as
        MANUALDEPWAIT, store available information, remove BuildQueue
        entry and release builder slave for another job.
        """
        build.status = BuildStatus.MANUALDEPWAIT
        build.storeBuildInfo(build, librarian, slave_status)
        logger.critical("***** %s is MANUALDEPWAIT *****"
                        % build.buildqueue_record.builder.name)
        build.buildqueue_record.builder.cleanSlave()
        build.buildqueue_record.destroySelf()

    @staticmethod
    def _handleStatus_CHROOTFAIL(build, librarian, slave_status,
                                 logger):
        """Handle a package that had failed when unpacking the CHROOT.

        Build has failed when installing the current CHROOT, mark the
        job as CHROOTFAIL, store available information, remove BuildQueue
        and release the builder.
        """
        build.status = BuildStatus.CHROOTWAIT
        build.storeBuildInfo(build, librarian, slave_status)
        logger.critical("***** %s is CHROOTWAIT *****" %
                        build.buildqueue_record.builder.name)
        build.buildqueue_record.builder.cleanSlave()
        build.notify()
        build.buildqueue_record.destroySelf()

    @staticmethod
    def _handleStatus_BUILDERFAIL(build, librarian, slave_status, logger):
        """Handle builder failures.

        Build has been failed when trying to build the target package,
        The environment is working well, so mark the job as NEEDSBUILD again
        and 'clean' the builder to do another jobs.
        """
        logger.warning("***** %s has failed *****"
                       % build.buildqueue_record.builder.name)
        build.buildqueue_record.builder.failBuilder(
            "Builder returned BUILDERFAIL when asked for its status")
        # simply reset job
        build.storeBuildInfo(build, librarian, slave_status)
        build.buildqueue_record.reset()

    @staticmethod
    def _handleStatus_GIVENBACK(build, librarian, slave_status, logger):
        """Handle automatic retry requested by builder.

        GIVENBACK pseudo-state represents a request for automatic retry
        later, the build records is delayed by reducing the lastscore to
        ZERO.
        """
        logger.warning("***** %s is GIVENBACK by %s *****"
                       % (build.buildqueue_record.specific_job.build.title,
                          build.buildqueue_record.builder.name))
        build.storeBuildInfo(build, librarian, slave_status)
        # XXX cprov 2006-05-30: Currently this information is not
        # properly presented in the Web UI. We will discuss it in
        # the next Paris Summit, infinity has some ideas about how
        # to use this content. For now we just ensure it's stored.
        build.buildqueue_record.builder.cleanSlave()
        build.buildqueue_record.reset()

    @staticmethod
    def createUploadLog(build, content, filename=None):
        """Creates a file on the librarian for the upload log.

        :return: ILibraryFileAlias for the upload log file.
        """
        # The given content is stored in the librarian, restricted as
        # necessary according to the targeted archive's privacy.  The content
        # object's 'upload_log' attribute will point to the
        # `LibrarianFileAlias`.

        assert build.upload_log is None, (
            "Upload log information already exists and cannot be overridden.")

        if filename is None:
            filename = 'upload_%s_log.txt' % build.id
        contentType = filenameToContentType(filename)
        file_size = len(content)
        file_content = StringIO(content)
        restricted = build.is_private

        return getUtility(ILibraryFileAliasSet).create(
            filename, file_size, file_content, contentType=contentType,
            restricted=restricted)

    def storeUploadLog(self, content):
        """See `IBuildBase`."""
        library_file = self.createUploadLog(self, content)
        self.upload_log = library_file

    @staticmethod
    def queueBuild(build, suspended=False):
        """See `IBuildBase`"""
        specific_job = build.makeJob()

        # This build queue job is to be created in a suspended state.
        if suspended:
            specific_job.job.suspend()

        duration_estimate = build.estimateDuration()
        queue_entry = BuildQueue(
            estimated_duration=duration_estimate,
            job_type=build.build_farm_job_type,
            job=specific_job.job, processor=specific_job.processor,
            virtualized=specific_job.virtualized)
        Store.of(build).add(queue_entry)
        return queue_entry
