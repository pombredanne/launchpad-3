
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

class ICVERefsView(IAddFormCustomization):
    """Bug Web Link views"""

class ICVERef(Interface):
    """A reference to a CVE number for a bug."""

    id = Int(
            title=_('ID'), required=True, readonly=True
            )
    bug = Int(
            title=_('Bug ID'), required=True, readonly=True,
            )
    cveref = TextLine(
            title=_('CVE Reference'), required=True, readonly=False,
            )
    title = Text(
            title=_('Title'), required=True, readonly=False,
            )
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True,
            )
    owner = Int(
            title=_('Owner'), required=False, readonly=True,
            )

    def url():
        """Return a URL to the site that has the CVE data for
        this CVE reference."""


class ICVERefSet(Interface):
    """A set for ICVERef objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a CVERef."""

    def __iter__():
        """Iterate through CVERefs for a given bug."""

