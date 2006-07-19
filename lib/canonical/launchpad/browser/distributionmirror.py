# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['DistributionMirrorEditView', 'DistributionMirrorFacets',
           'DistributionMirrorOverviewMenu', 'DistributionMirrorAddView',
           'DistributionMirrorUploadFileListView', 'DistributionMirrorView',
           'DistributionMirrorOfficialApproveView']

from StringIO import StringIO

from zope.component import getUtility
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.content_types import guess_content_type
from zope.event import notify

from sourcerer.deb.version import Version

from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.webapp.generalform import GeneralFormView
from canonical.launchpad.webapp import (
    canonical_url, StandardLaunchpadFacets, Link, ApplicationMenu, 
    enabled_with_permission)
from canonical.launchpad.interfaces import (
    IDistributionMirror, validate_distribution_mirror_schema,
    ILibraryFileAliasSet)
from canonical.launchpad.browser.editview import SQLObjectEditView


class DistributionMirrorFacets(StandardLaunchpadFacets):

    usedfor = IDistributionMirror
    enable_only = ['overview']


class DistributionMirrorOverviewMenu(ApplicationMenu):

    usedfor = IDistributionMirror
    facet = 'overview'
    links = ['edit', 'admin']

    def edit(self):
        text = 'Edit Details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        text = 'Mark as Official'
        return Link('+mark-official', text, icon='edit')


class _FlavoursByDistroRelease:
    """A simple class to help when rendering a table of releases and flavours
    mirrored by a given Release mirror.
    """

    def __init__(self, distrorelease, flavours):
        self.distrorelease = distrorelease
        self.flavours = flavours


class DistributionMirrorView(LaunchpadView):

    def getSummarizedMirroredSourceReleases(self):
        mirrors = self.context.getSummarizedMirroredSourceReleases()
        return sorted(mirrors, reverse=True,
                      key=lambda mirror: Version(mirror.distrorelease.version))

    def getSummarizedMirroredArchReleases(self):
        mirrors = self.context.getSummarizedMirroredArchReleases()
        return sorted(
            mirrors, reverse=True,
            key=lambda mirror: Version(
                mirror.distro_arch_release.distrorelease.version))

    def getCDImageMirroredFlavoursByRelease(self):
        """Return a list of _FlavoursByDistroRelease objects ordered
        descending by version.
        """
        releases = {}
        for cdimage in self.context.cdimage_releases:
            release, flavour = cdimage.distrorelease, cdimage.flavour
            flavours_by_release = releases.get(release)
            if flavours_by_release is None:
                flavours_by_release = _FlavoursByDistroRelease(release, [])
                releases[release] = flavours_by_release
            flavours_by_release.flavours.append(flavour)
        flavours_by_releases = releases.values()
        return sorted(flavours_by_releases, reverse=True,
                      key=lambda item: Version(item.distrorelease.version))


class DistributionMirrorAddView(GeneralFormView):

    def validate(self, form_values):
        validate_distribution_mirror_schema(form_values)

    def process(self, owner, displayname, description, speed, country,
                content, http_base_url, ftp_base_url, rsync_base_url, enabled,
                official_candidate):
        mirror = self.context.newMirror(
            owner=owner, speed=speed, country=country, content=content,
            displayname=displayname, description=description, enabled=enabled,
            http_base_url=http_base_url, ftp_base_url=ftp_base_url,
            rsync_base_url=rsync_base_url,
            official_candidate=official_candidate)

        self._nextURL = canonical_url(mirror)
        notify(ObjectCreatedEvent(mirror))
        return mirror
        

class DistributionMirrorOfficialApproveView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))


class DistributionMirrorEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))

    def validate(self, form_values):
        validate_distribution_mirror_schema(form_values)


class DistributionMirrorUploadFileListView(GeneralFormView):

    def process(self, file_list=None):
        if file_list is not None:
            filename = self.request.get('field.file_list').filename
            content_type, encoding = guess_content_type(
                name=filename, body=file_list)
            library_file = getUtility(ILibraryFileAliasSet).create(
                name=filename, size=len(file_list),
                file=StringIO(file_list), contentType=content_type)
            self.context.file_list = library_file
        self._nextURL = canonical_url(self.context)

