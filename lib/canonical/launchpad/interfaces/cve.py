# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""CVE interfaces."""

__metaclass__ = type

__all__ = [
    'ICve',
    'ICveSet',
    ]

from zope.i18nmessageid import MessageIDFactory
from zope.interface import Interface, Attribute
from zope.schema import Choice, Datetime, Int, TextLine

from canonical.launchpad.validators.cve import valid_cve
from canonical.launchpad.interfaces.buglink import IBugLinkTarget
from canonical.lp.dbschema import CveStatus

_ = MessageIDFactory('launchpad')

class ICve(IBugLinkTarget):
    """A single CVE database entry."""

    id = Int(title=_('ID'), required=True, readonly=True)
    sequence = TextLine(
        title=_('CVE Sequence Number'),
        description=_('The CVE sequence number '
            'should take the form of XXXX-XXXX, all digits. '
            'We will poll the CVE database to determine the status of '
            'the CVE automatically.'),
        required=True, readonly=False, constraint=valid_cve)
    status = Choice(title=_('Current CVE State'), 
        default=CveStatus.CANDIDATE, description=_("Whether or not the "
        "vulnerability has been reviewed and assigned a full CVE number, "
        "or is still considered a Candidate, or is deprecated."),
        required=True, vocabulary='CveStatus')
    description = TextLine(
        title=_('Title'),
        description=_('A description of the CVE issue. This will be '
            'updated regularly from the CVE database.'),
        required=True, readonly=False)
    datecreated = Datetime(
        title=_('Date Created'), required=True, readonly=True)
    datemodified = Datetime(
        title=_('Date Modified'), required=True, readonly=False)

    # other attributes
    url = Attribute("Return a URL to the site that has the CVE data for "
        "this CVE reference.")
    displayname = Attribute("A very brief name describing the ref and state.")
    title = Attribute("A title for the CVE")
    references = Attribute("The set of CVE References for this CVE.")

    def createReference(source, content, url=None):
        """Create a new CveReference for this CVE."""

    def removeReference(ref):
        """Remove a CveReference."""


class ICveSet(Interface):
    """The set of ICve objects."""

    title = Attribute('Title')

    def __getitem__(key):
        """Get a Cve by sequence number."""

    def __iter__():
        """Iterate through all the Cve records."""

    def new(sequence, description, cvestate=CveStatus.CANDIDATE):
        """Create a new ICve."""

    def latest(quantity=5):
        """Return the most recently created CVE's, newest first, up to the
        number given in quantity."""

    def latest_modified(quantity=5):
        """Return the most recently modified CVE's, newest first, up to the
        number given in quantity."""

    def search(text):
        """Search the CVE database for matching CVE entries."""

    def inText(text):
        """Find one or more Cve's by analysing the given text.
        
        This will look for references to CVE or CAN numbers, and return the
        CVE references. It will create any CVE's that it sees which are
        already not in the database. It returns the list of all the CVE's it
        found in the text.
        """

    def inMessage(msg):
        """Find any CVE's in the given message.

        This will create any CVE's that it does not already know about. It
        returns a list of all the CVE's that it saw mentioned in the
        message.
        """

