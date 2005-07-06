
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.launchpad.validators.cve import valid_cve
from canonical.lp.dbschema import CVEState

class ICVERefsView(IAddFormCustomization):
    """Bug Web Link views"""

class ICVERef(Interface):
    """A reference to a CVE number for a bug."""

    id = Int(title=_('ID'), required=True, readonly=True)
    bug = Int(title=_('Bug ID'), required=True, readonly=True)
    cveref = TextLine(
        title=_('CVE Reference'),
        description=_('The CVE reference number related to this bug. '
            'It should take the form of XXXX-XXXX, all digits. Below, '
            'you should indicate whether it is a CANdidate or an actual '
            'CVE number.'),
        required=True, readonly=False, constraint=valid_cve)
    cvestate = Choice(title=_('Current CVE State'), 
        default=CVEState.CAN, description=_("Whether or not the "
        "vulnerability has been reviewed and assigned a full CVE number, "
        "or is still considered a CANdidated."), required=True,
        vocabulary='CVEState')
    title = TextLine(
        title=_('Title'),
        description=_('A brief summary of the CVE issue. This will be '
            'displayed on the bug page.'),
        required=True, readonly=False)
    datecreated = Datetime(
        title=_('Date Created'), required=True, readonly=True)
    owner = Int(
        title=_('Owner'), required=False, readonly=True)

    url = Attribute("Return a URL to the site that has the CVE data for "
        "this CVE reference.")
    displayname = Attribute("A very brief name describing the ref and state.")


class ICVERefSet(Interface):
    """A set for ICVERef objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    title = Attribute('Title')

    def __getitem__(key):
        """Get a CVERef."""

    def __iter__():
        """Iterate through CVERefs for a given bug."""

    def createCVERef(bug, cveref, cvestate, title, owner):
        """Create an ICVERef attached to bug.

        Returns the ICVERef that was created.
        """

    def fromText(text, bug, title, owner):
        """Create one or more CVERef's by analysing the given text. This
        will look for references to CVE or CAN numbers, and create the
        relevant details.
        """

    def fromMessage(message, bug):
        """Create one or more CVERef's by analysing the given email. The
        owner of the CVERef's will be the sender of the message.
        It returns a (possibly empty) list of CVERef's created.
        """

