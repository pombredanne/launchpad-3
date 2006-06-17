# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugMessage-related browser view classes."""

__metaclass__ = type
__all__ = [
    'BugMessageAddFormView']

from StringIO import StringIO

from canonical.launchpad.interfaces import IBugMessageAddForm as form_schema
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.generalform import GeneralFormView

class BugMessageAddFormView(GeneralFormView):
    """Browser view class for adding a bug comment/attachment."""

    def process(self,
                include_attachment=form_schema['include_attachment'].default,
                filecontent=form_schema['filecontent'].default,
                patch=form_schema['patch'].default,
                title=form_schema['title'].default,
                comment=form_schema['comment'].default,
                email_me=form_schema['email_me'].default):
        """Add the comment and/or attachment."""
        bug = self.context.bug

        # XXX: Write proper FileUpload field and widget instead of this
        # hack. -- Bjorn Tillenius, 2005-06-16
        file_ = self.request.form[self.filecontent_widget.name]

        message = None
        if comment or (include_attachment and file_):
            message = bug.newMessage(
                subject=title or bug.followup_subject(),
                content=comment, owner=self.user)

        if not (include_attachment and file_):
            return

        # Process the attachment.
        bug.addAttachment(
            owner=self.user, file_=StringIO(filecontent),
            filename=file_.filename, description=title,
            comment=message, is_patch=patch)

        # Subscribe the user to the bug report, if requested.
        if email_me:
            bug.subscribe(self.user)

    def shouldShowEmailMeWidget(self):
        """Should the subscribe checkbox be shown?"""
        return (not self.context.bug.isSubscribed(self.user))

    def nextURL(self):
        """Redirect to the main bug page."""
        self.request.response.redirect(canonical_url(self.context))
