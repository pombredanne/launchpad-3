
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.launchpad.validators.cve import valid_cve

class ICVERefsView(IAddFormCustomization):
    """Bug Web Link views"""

class ICVERef(Interface):
    """A reference to a CVE number for a bug."""

    id = Int(title=_('ID'), required=True, readonly=True)
    bug = Int(title=_('Bug ID'), required=True, readonly=True)
    cveref = TextLine(
        title=_('CVE Reference'),
        description=_('The CVE reference number related to this bug.'),
        required=True, readonly=False, constraint=valid_cve)
    title = TextLine(
        title=_('Title'),
        description=_('A brief description of the content that is being linked to.'),
        required=True, readonly=False)
    datecreated = Datetime(
        title=_('Date Created'), required=True, readonly=True)
    owner = Int(
        title=_('Owner'), required=False, readonly=True)

    def url():
        """Return a URL to the site that has the CVE data for
        this CVE reference."""


class ICVERefSet(Interface):
    """A set for ICVERef objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    title = Attribute('Title')

    def __getitem__(key):
        """Get a CVERef."""

    def __iter__():
        """Iterate through CVERefs for a given bug."""

    def createCVERef(bug, cveref, title, owner):
        """Create an ICVERef attached to bug.

        Returns the ICVERef that was created.
        """
