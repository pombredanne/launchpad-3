from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

class IBugExternalRefsView(IAddFormCustomization):
    """BugExternalRef views"""

class IBugExternalRef(Interface):
    """An external reference for a bug, not supported remote bug systems."""

    id = Int(
            title=_('ID'), required=True, readonly=True
            )
    bug = Int(
            title=_('Bug ID'), required=True, readonly=True,
            )
    bugreftype = Choice(
            title=_('Bug Ref Type'), required=True, readonly=False,
            vocabulary='BugRef',
            )
    data = TextLine(
            title=_('Data'), required=True, readonly=False,
            )
    description = Text(
            title=_('Description'), required=True, readonly=False,
            )
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True,
            )
    owner = Int(
            title=_('Owner'), required=False, readonly=True,
            )

    def url():
        """Return the url of the external resource."""



class IBugExternalRefSet(Interface):
    """A set for IBugExternalRef objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a BugExternalRef."""

    def __iter__():
        """Iterate through BugExternalRefs for a given bug."""

