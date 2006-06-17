# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Bug attachment views."""

__metaclass__ = type
__all__ = [
    'BugAttachmentSetNavigation',
    'BugAttachmentEdit']

from cStringIO import StringIO

from zope.component import getUtility
from zope.interface import implements
from zope.app.content_types import guess_content_type

from canonical.lp import Passthrough
from canonical.lp.dbschema import BugAttachmentType
from canonical.launchpad.webapp import canonical_url, GetitemNavigation
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.interfaces import (
    IBugAttachment, IBugAttachmentSet, IBug, ILibraryFileAliasSet,
    IBugAttachmentEditForm, ILaunchBag)


class BugAttachmentSetNavigation(GetitemNavigation):

    usedfor = IBugAttachmentSet


class BugAttachmentEdit:
    """Edits a bug attachment."""
    implements(IBugAttachmentEditForm)

    title = Passthrough('title', 'attachment')

    def __init__(self, attachment):
        self.attachment = attachment

    def _set_contenttype(self, new_contenttype):
        # If it's a patch, 'text/plain' is always used.
        if self.patch and new_contenttype != 'text/plain':
            return
        filealiasset = getUtility(ILibraryFileAliasSet)
        old_filealias = self.attachment.libraryfile
        # Download the file and upload it again with the new content
        # type.
        # XXX: It should be possible to simply create a new filealias
        # with the same content as the old one.
        # -- Bjorn Tillenius, 2005-06-30
        old_content = old_filealias.read()
        self.attachment.libraryfile = filealiasset.create(
            name=old_filealias.filename, size=len(old_content),
            file=StringIO(old_content), contentType=new_contenttype)
    contenttype = property(
        lambda self: self.attachment.libraryfile.mimetype, _set_contenttype)

    def _set_patch(self, new_value):
        if new_value:
            self.attachment.type = BugAttachmentType.PATCH
            # Patches are always text.
            self.contenttype = 'text/plain'
        else:
            self.attachment.type = BugAttachmentType.UNSPECIFIED
    patch = property(
        lambda self: self.attachment.type == BugAttachmentType.PATCH,
        _set_patch)
