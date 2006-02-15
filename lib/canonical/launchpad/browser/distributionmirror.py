# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['DistributionMirrorEditView', 'DistributionMirrorFacets',
           'DistributionMirrorOverviewMenu', 'DistributionMirrorAddView',
           'DistributionMirrorUploadFileListView']

from StringIO import StringIO

from zope.component import getUtility
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.content_types import guess_content_type
from zope.event import notify

from canonical.lp.dbschema import MirrorContent
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

    def initialize(self):
        if (self.context.content != MirrorContent.ARCHIVE
            and 'upload_file_list' not in self.links):
            self.links.append('upload_file_list')

    def edit(self):
        text = 'Edit Details'
        return Link('+edit', text, icon='edit')

    def upload_file_list(self):
        text = 'Upload File List'
        return Link('+uploadfilelist', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def admin(self):
        text = 'Administer this Mirror'
        return Link('+admin', text, icon='edit')


class DistributionMirrorAddView(GeneralFormView):

    # XXX: This is a workaround while
    # https://launchpad.net/products/launchpad/+bug/5792 isn't fixed.
    __launchpad_facetname__ = 'overview'

    def validate(self, form_values):
        validate_distribution_mirror_schema(form_values)

    def process(self, owner, name, displayname, description, speed, country,
                content, http_base_url, ftp_base_url, rsync_base_url,
                pulse_type, pulse_source, enabled, official_candidate):
        mirror = self.context.newMirror(
            owner=owner, name=name, speed=speed, country=country,
            content=content, pulse_type=pulse_type, displayname=displayname,
            description=description, http_base_url=http_base_url,
            ftp_base_url=ftp_base_url, rsync_base_url=rsync_base_url,
            official_candidate=official_candidate, enabled=enabled,
            pulse_source=pulse_source)

        self._nextURL = canonical_url(mirror)
        notify(ObjectCreatedEvent(mirror))
        return mirror
        

class DistributionMirrorEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))

    def validate(self, form_values):
        validate_distribution_mirror_schema(form_values)


class DistributionMirrorUploadFileListView(GeneralFormView):

    # XXX: This is a workaround while
    # https://launchpad.net/products/launchpad/+bug/5792 isn't fixed.
    __launchpad_facetname__ = 'overview'

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

