# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugMessage-related browser view classes."""

__metaclass__ = type
__all__ = [
    'BugMessageAddFormView']

from StringIO import StringIO

from zope.app.form.interfaces import WidgetsError, MissingInputError
from zope.schema import ValidationError

from canonical.launchpad.interfaces import IBugMessageAddForm
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.generalform import GeneralFormView

class BugMessageAddFormView(GeneralFormView):
    """Browser view class for adding a bug comment/attachment."""

    schema = IBugMessageAddForm

    @property
    def initial_values(self):
        return dict(
            subject=self.context.bug.followup_subject())

    def process(self, include_attachment=None, subject=None, filecontent=None,
                patch=None, attachment_description=None, comment=None,
                email_me=None):
        """Add the comment and/or attachment."""
        bug = self.context.bug

        if email_me:
            bug.subscribe(self.user)

        # XXX: Write proper FileUpload field and widget instead of this
        # hack. -- Bjorn Tillenius, 2005-06-16
        file_ = self.request.form.get(self.filecontent_widget.name)

        message = None
        if comment or (include_attachment and file_):
            message = bug.newMessage(
                subject=subject, content=comment, owner=self.user)

            # An blank comment with only a subect line is always added
            # when the user attaches a file, so show the add comment
            # feedback message only when the user actually added a
            # comment.
            if comment:
                self.request.response.addNotification(
                    "Thank you for your comment.")

        if not (include_attachment and file_):
            return

        # Slashes in filenames cause problems, convert them to dashes
        # instead.
        filename = file_.filename.replace('/', '-')

        # Process the attachment.
        bug.addAttachment(
            owner=self.user, file_=StringIO(filecontent),
            filename=filename, description=attachment_description,
            comment=message, is_patch=patch)

        self.request.response.addNotification(
            "Attachment %(filename)s added to bug.", filename=filename)

    @property
    def _keyword_arguments(self):
        return self.fieldNames

    def shouldShowEmailMeWidget(self):
        """Should the subscribe checkbox be shown?"""
        return (not self.context.bug.isSubscribed(self.user))

    def nextURL(self):
        """Redirect to the main bug page."""
        self.request.response.redirect(canonical_url(self.context))
