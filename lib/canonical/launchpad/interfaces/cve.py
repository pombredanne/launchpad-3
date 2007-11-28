# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""CVE interfaces."""

__metaclass__ = type

__all__ = [
    'CveStatus',
    'ICve',
    'ICveSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice, Datetime, Int, TextLine

from canonical.launchpad import _
from canonical.launchpad.interfaces.validation import valid_cve_sequence

from canonical.lazr import DBEnumeratedType, DBItem


class CveStatus(DBEnumeratedType):
    """The Status of this item in the CVE Database.

    When a potential problem is reported to the CVE authorities they assign
    a CAN number to it. At a later stage, that may be converted into a CVE
    number. This indicator tells us whether or not the issue is believed to
    be a CAN or a CVE.
    """

    CANDIDATE = DBItem(1, """
        Candidate

        The vulnerability is a candidate which hasn't yet been confirmed and
        given "Entry" status.
        """)

    ENTRY = DBItem(2, """
        Entry

        This vulnerability or threat has been assigned a CVE number, and is
        fully documented. It has been through the full CVE verification
        process.
        """)

    DEPRECATED = DBItem(3, """
        Deprecated

        This entry is deprecated, and should no longer be referred to in
        general correspondence. There is either a newer entry that better
        defines the problem, or the original candidate was never promoted to
        "Entry" status.
        """)


class ICve(Interface):
    """A single CVE database entry."""

    id = Int(title=_('ID'), required=True, readonly=True)
    sequence = TextLine(
        title=_('CVE Sequence Number'),
        description=_('Should take the form XXXX-XXXX, all digits.'),
        required=True, readonly=False, constraint=valid_cve_sequence)
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

    def getAll():
        """Return all ICVEs"""

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

    def getBugCvesForBugTasks(bugtasks):
        """Return BugCve objects that correspond to the supplied bugtasks.

        Returns an iterable of BugCve objects for bugs related to the
        supplied sequence of bugtasks.
        """

    def getBugCveCount():
        """Return the number of CVE bug links there is in Launchpad."""
