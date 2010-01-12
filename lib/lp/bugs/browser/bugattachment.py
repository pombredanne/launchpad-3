# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Bug attachment views."""

__metaclass__ = type
__all__ = [
    'BugAttachmentContentCheck',
    'BugAttachmentSetNavigation',
    'BugAttachmentEditView',
    'BugAttachmentURL',
    ]

from cStringIO import StringIO

from zope.interface import implements
from zope.component import getUtility
from zope.contenttype import guess_content_type

from canonical.launchpad.webapp import canonical_url, GetitemNavigation
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.bugs.interfaces.bugattachment import (
    BugAttachmentType, IBugAttachmentEditForm, IBugAttachmentSet)
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from canonical.launchpad.webapp.launchpadform import (
    action, LaunchpadFormView)
from canonical.launchpad.webapp.menu import structured

from canonical.lazr.utils import smartquote


class BugAttachmentContentCheck:
    """A mixin class that checks the consistency of patch flag and file type.
    """

    def guess_content_type(self, filename, file_content):
        """Guess the content type a file with the given anme and content."""
        guessed_type, encoding = guess_content_type(
            name=filename, body=file_content)
        return guessed_type

    def attachment_type_consistent_with_content_type(
        self, patch_flag_set, filename, file_content):
        """Return True iff patch_flag is consistent with filename and content.
        """
        guessed_type = self.guess_content_type(filename, file_content)
        # An XOR of "is the patch flag selected?" with "is the
        # guessed type not a diff?" tells us if the type selected
        # b y the user matches the guessed type.
        return (patch_flag_set ^ (guessed_type != 'text/x-diff'))

    def next_url_for_inconsistent_patch_flags(self, attachment):
        """The next_url value used for an inconistent patch flag."""
        return canonical_url(attachment) + '?need_confirm=1'


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

class BugAttachmentEditView(LaunchpadFormView, BugAttachmentContentCheck):
    """Edit a bug attachment."""

    schema = IBugAttachmentEditForm
    field_names = ['title', 'patch', 'contenttype']

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
            filename = self.context.libraryfile.filename
            file_content = self.context.libraryfile.read()
            # We expect that users set data['patch'] to True only for
            # real patch data, indicated by guessed_content_type ==
            # 'text/x-diff'. If there are inconsistencies, we don't
            # set the value automatically, but show the user this form
            # again with an explanation of when the flag data['patch']
            # should be used.
            new_type_consistent_with_guessed_type = (
                self.attachment_type_consistent_with_content_type(
                    new_type == BugAttachmentType.PATCH, filename,
                    file_content))
            is_confirmation_step = self.request.form_ng.getOne(
                'confirmation_step') is not None
            if new_type_consistent_with_guessed_type or is_confirmation_step:
                self.context.type = new_type
            else:
                self.next_url = self.next_url_for_inconsistent_patch_flags(
                    self.context)

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
            'Attachment "<a href="%(url)s">%(name)s</a>" has been deleted.',
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

    @property
    def label(self):
        return smartquote('Bug #%d - Edit attachment "%s"') % (
            self.context.bug.id, self.context.title)

    @property
    def rendering_confirmation_step(self):
        """Is the page is displayed to confirm an unexpected "patch" value?"""
        return self.request.get('need_confirm') is not None

    @property
    def confirmation_element(self):
        """An extra hidden input field for the patch flag confirmation step.
        """
        if self.rendering_confirmation_step:
            return ('<input type="hidden" name="confirmation_step" '
                    'value="1"/>')
        else:
            return ''

    @property
    def is_patch(self):
        """True if this attachment contains a patch, else False."""
        return self.context.type == BugAttachmentType.PATCH

    page_title = label
