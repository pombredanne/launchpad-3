# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'PackageBuildMixin',
    ]


from cStringIO import StringIO

import six
from zope.component import getUtility

from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.model.buildfarmjob import BuildFarmJobMixin
from lp.services.helpers import filenameToContentType
from lp.services.librarian.browser import ProxiedLibraryFileAlias
from lp.services.librarian.interfaces import ILibraryFileAliasSet
from lp.soyuz.adapters.archivedependencies import (
    default_component_dependency_name,
    )
from lp.soyuz.interfaces.component import IComponentSet


class PackageBuildMixin(BuildFarmJobMixin):

    @property
    def current_component(self):
        """See `IPackageBuild`."""
        return getUtility(IComponentSet)[default_component_dependency_name]

    @property
    def upload_log_url(self):
        """See `IPackageBuild`."""
        if self.upload_log is None:
            return None
        return ProxiedLibraryFileAlias(self.upload_log, self).http_url

    @property
    def log_url(self):
        """See `IBuildFarmJob`."""
        if self.log is None:
            return None
        return ProxiedLibraryFileAlias(self.log, self).http_url

    @property
    def is_private(self):
        """See `IBuildFarmJob`"""
        return self.archive.private

    def updateStatus(self, status, builder=None, slave_status=None,
                     date_started=None, date_finished=None,
                     force_invalid_transition=False):
        super(PackageBuildMixin, self).updateStatus(
            status, builder=builder, slave_status=slave_status,
            date_started=date_started, date_finished=date_finished,
            force_invalid_transition=force_invalid_transition)

        if (status == BuildStatus.MANUALDEPWAIT and slave_status is not None
            and slave_status.get('dependencies') is not None):
            self.dependencies = unicode(slave_status.get('dependencies'))
        else:
            self.dependencies = None

    def verifySuccessfulUpload(self):
        """See `IPackageBuild`."""
        raise NotImplementedError

    def createUploadLog(self, content, filename=None):
        """Creates a file on the librarian for the upload log.

        :return: ILibraryFileAlias for the upload log file.
        """
        # The given content is stored in the librarian, restricted as
        # necessary according to the targeted archive's privacy.  The content
        # object's 'upload_log' attribute will point to the
        # `LibrarianFileAlias`.

        assert self.upload_log is None, (
            "Upload log information already exists and cannot be overridden.")

        if filename is None:
            filename = 'upload_%s_log.txt' % self.id
        contentType = filenameToContentType(filename)
        content = six.ensure_binary(content)
        file_size = len(content)
        file_content = StringIO(content)
        restricted = self.is_private

        return getUtility(ILibraryFileAliasSet).create(
            filename, file_size, file_content, contentType=contentType,
            restricted=restricted)

    def storeUploadLog(self, content):
        """See `IPackageBuild`."""
        filename = "upload_%s_log.txt" % self.id
        library_file = self.createUploadLog(content, filename=filename)
        self.upload_log = library_file

    def notify(self, extra_info=None):
        """See `IPackageBuild`."""
        raise NotImplementedError

    def getUploader(self, changes):
        """See `IPackageBuild`."""
        raise NotImplementedError
