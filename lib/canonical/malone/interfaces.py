# arch-tag: 2C926820-E0AE-11D8-A7D9-000D9329A36C

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('malone')
from zope.interface import Interface

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.database.malone import IBug, IBugAttachment


class IMaloneApplication(Interface):
    """Malone application class."""

class IMaloneBug(IBug, IAddFormCustomization):
    pass

class IMaloneBugAttachment(IBugAttachment, IAddFormCustomization):
    pass

# Interfaces for containers

class IBugContainer(IAddFormCustomization):
    """A container for bugs."""

    def __getitem__(key):
        """Get a Bug."""

    def __iter__():
        """Iterate through Bugs."""

class IBugAttachmentContainer(IAddFormCustomization):
    """A container for IBugAttachment objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get an Attachment."""

    def __iter__():
        """Iterate through BugAttachments for a given bug."""

class IBugExternalRefContainer(Interface):
    """A container for IBugExternalRef objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a BugExternalRef."""

    def __iter__():
        """Iterate through BugExternalRefs for a given bug."""

class IProjectContainer(Interface):
    """A container for IProject objects."""

    def __getitem__(key):
        """Get a Project by name."""

    def __iter__():
        """Iterate through Projects."""

    def search(name, title):
        """Search through Projects."""

class ISourcepackageContainer(Interface):
    """A container for ISourcepackage objects."""

    def __getitem__(key):
        """Get an ISourcepackage by name"""

    def __iter__():
        """Iterate through Sourcepacages."""

class IBugSubscriptionContainer(Interface):
    """A container for IBugSubscription objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a BugSubscription object."""

    def __iter__():
        """Iterate through bug subscribers for this bug."""

    def delete(id):
        """Delete a subscription."""

class IBugMessagesView(IAddFormCustomization):
    """BugMessage views"""

class IBugExternalRefsView(IAddFormCustomization):
    """BugExternalRef views"""

