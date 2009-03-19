# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Bug attachment views."""

__metaclass__ = type
__all__ = [
    'BugAttachmentSetNavigation',
    'BugAttachmentEditView',
    'BugAttachmentURL',
    ]

from cStringIO import StringIO

from zope.interface import implements
from zope.component import getUtility

from canonical.launchpad.webapp import canonical_url, GetitemNavigation
from canonical.launchpad.interfaces import (
    BugAttachmentType, IBugAttachmentSet, ILibraryFileAliasSet,
    IBugAttachmentEditForm, ILaunchBag)
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from canonical.launchpad.webapp.launchpadform import (
    action, LaunchpadFormView)
from canonical.launchpad.webapp.menu import structured


class BugAttachmentSetNavigation(GetitemNavigation):

    usedfor = IBugAttachmentSet


class BugAttachmentURL:
    """Bug URL creation rules."""
    implements(ICanonicalUrlData)

    rootsite = 'bugs'

    def __init__(self, context):
        self.context = context

    @property
    def inside(self):
        """Always relative to a traversed bugtask."""
        bugtask = getUtility(ILaunchBag).bugtask
        if bugtask is None:
            return self.context.bug
        else:
            return bugtask

    @property
    def path(self):
        """Return the path component of the URL."""
        return u"+attachment/%d" % self.context.id


class BugAttachmentEditView(LaunchpadFormView):
    """Edit a bug attachment."""

    schema = IBugAttachmentEditForm
    field_names = ['title', 'patch', 'contenttype']
    label = "Change bug attachment information"

    def __init__(self, context, request):
        LaunchpadFormView.__init__(self, context, request)
        self.next_url = self.cancel_url = (
            canonical_url(ICanonicalUrlData(context).inside))

    @property
    def initial_values(self):
        attachment = self.context
        return dict(
            title=attachment.title,
            patch=attachment.type == BugAttachmentType.PATCH,
            contenttype=attachment.libraryfile.mimetype)

    @action('Change', name='change')
    def change_action(self, action, data):
        if data['patch']:
            new_type = BugAttachmentType.PATCH
        else:
            new_type = BugAttachmentType.UNSPECIFIED
        if new_type != self.context.type:
            self.context.type = new_type

        if data['title'] != self.context.title:
            self.context.title = data['title']

        # If it's a patch, 'text/plain' is always used.
        if (self.context.type == BugAttachmentType.PATCH
            and data['contenttype'] != 'text/plain'):
            data['contenttype'] = 'text/plain'
        if self.context.libraryfile.mimetype != data['contenttype']:
            self.updateContentType(data['contenttype'])

    @action('Delete Attachment', name='delete')
    def delete_action(self, action, data):
        self.request.response.addInfoNotification(structured(
            'Attachment "<a href="%(url)s">%(name)s</a>" has been deleted.'
            ' It will be possible to download it until it has been'
            ' automatically removed from the server.',
            url=self.context.libraryfile.http_url, name=self.context.title))
        self.context.removeFromBug(user=self.user)

    def updateContentType(self, new_content_type):
        """Update the attachment content type."""
        filealiasset = getUtility(ILibraryFileAliasSet)
        old_filealias = self.context.libraryfile
        # Download the file and upload it again with the new content
        # type.
        # XXX: Bjorn Tillenius 2005-06-30:
        # It should be possible to simply create a new filealias
        # with the same content as the old one.
        old_content = old_filealias.read()
        self.context.libraryfile = filealiasset.create(
            name=old_filealias.filename, size=len(old_content),
            file=StringIO(old_content), contentType=new_content_type)
