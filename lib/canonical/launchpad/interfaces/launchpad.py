# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Interfaces pertaining to the launchpad application.

Note that these are not interfaces to application content objects.
"""
__metaclass__ = type

from zope.interface import Interface, Attribute
import zope.exceptions
import zope.app.publication.interfaces
import zope.publisher.interfaces.browser
import zope.app.traversing.interfaces
from zope.schema import Int, Choice
from persistent import IPersistent

from canonical.launchpad import _
from canonical.launchpad.webapp.interfaces import ILaunchpadApplication

# XXX These import shims are actually necessary if we don't go over the
# entire codebase and fix where the import should come from.
#   -- kiko, 2007-02-08
from canonical.launchpad.webapp.interfaces import (
    NotFoundError, ILaunchpadRoot, ILaunchBag, IOpenLaunchBag, IBreadcrumb,
    IBasicLaunchpadRequest, IAfterTraverseEvent, AfterTraverseEvent,
    IBeforeTraverseEvent, BeforeTraverseEvent,
    )

__all__ = [
    'NotFoundError', 'ILaunchpadRoot', 'ILaunchBag', 'IOpenLaunchBag',
    'NameNotAvailable', 'UnexpectedFormData',
    'IMaloneApplication', 'IRosettaApplication', 'IRegistryApplication',
    'IBazaarApplication', 'IPasswordEncryptor', 'IReadZODBAnnotation',
    'IWriteZODBAnnotation', 'IZODBAnnotation',
    'IHasOwner', 'IHasDrivers', 'IHasAssignee', 'IHasProduct',
    'IHasProductAndAssignee', 'IAging', 'IHasDateCreated', 'IHasBug',
    'ICrowd', 'ILaunchpadCelebrities', 'IAuthApplication',
    'IPasswordChangeApp', 'IPasswordResets', 'IShipItApplication',
    'IAfterTraverseEvent', 'AfterTraverseEvent',
    'IBeforeTraverseEvent', 'BeforeTraverseEvent', 'IBreadcrumb',
    'IBasicLaunchpadRequest', 'IHasSecurityContact', 'IHasAppointedDriver'
    'IStructuralObjectPresentation',
    ]


class NameNotAvailable(KeyError):
    """You're trying to set a name, but the name you chose is not available."""


class UnexpectedFormData(AssertionError):
    """Got form data that is not what is expected by a form handler."""


class ILaunchpadCelebrities(Interface):
    """Well known things.

    Celebrities are SQLBase instances that have a well known name.
    """
    admin = Attribute("The 'admins' team.")
    ubuntu = Attribute("The Ubuntu Distribution.")
    debian = Attribute("The Debian Distribution.")
    rosetta_expert = Attribute("The Rosetta Experts team.")
    vcs_imports = Attribute("The 'vcs-imports' team.")
    bazaar_expert = Attribute("The Bazaar Experts team.")
    debbugs = Attribute("The Debian Bug Tracker")
    sourceforge_tracker = Attribute("The SourceForge Bug Tracker")
    shipit_admin = Attribute("The ShipIt Administrators.")
    launchpad_developers = Attribute("The Launchpad development team.")
    ubuntu_bugzilla = Attribute("The Ubuntu Bugzilla.")
    bug_watch_updater = Attribute("The Bug Watch Updater.")
    bug_importer = Attribute("The bug importer.")
    landscape = Attribute("The Landscape project.")
    launchpad = Attribute("The Launchpad product.")
    support_tracker_janitor = Attribute("The Support Tracker Janitor.")
    team_membership_janitor = Attribute("The Team Membership Janitor.")


class ICrowd(Interface):

    def __contains__(person_or_team_or_anything):
        """Return True if the given person_or_team_or_anything is in the crowd.

        Note that a particular crowd can choose to answer 'True' to this
        question, if that is what it is supposed to do.  So, crowds that
        contain other crowds will want to allow the other crowds the
        opportunity to answer __contains__ before that crowd does.
        """

    def __add__(crowd):
        """Return a new ICrowd that is this crowd added to the given crowd.

        The returned crowd contains the person or teams in
        both this crowd and the given crowd.
        """


class IMaloneApplication(ILaunchpadApplication):
    """Application root for malone."""

    bug_count = Attribute("The number of bugs recorded in Malone")
    bugwatch_count = Attribute("The number of links to external bug trackers")
    bugextref_count = Attribute("The number of links to outside URL's")
    bugtask_count = Attribute("The number of bug tasks in Malone")
    bugtracker_count = Attribute("The number of bug trackers in Malone")
    top_bugtrackers = Attribute("The BugTrackers with the most watches.")
    latest_bugs = Attribute("The latest 5 bugs filed.")


class IRosettaApplication(ILaunchpadApplication):
    """Application root for rosetta."""

    statsdate = Attribute("""The date stats were last updated.""")

    def translatable_products():
        """Return a list of the translatable products."""

    def translatable_distroreleases():
        """Return a list of the distroreleases in launchpad for which
        translations can be done.
        """

    def translation_groups():
        """Return a list of the translation groups in the system."""

    def potemplate_count():
        """Return the number of potemplates in the system."""

    def pofile_count():
        """Return the number of pofiles in the system."""

    def pomsgid_count():
        """Return the number of msgs in the system."""

    def translator_count():
        """Return the number of people who have given translations."""

    def language_count():
        """Return the number of languages Rosetta can translate into."""


class IRegistryApplication(ILaunchpadApplication):
    """Registry application root."""


class IShipItApplication(ILaunchpadApplication):
    """ShipIt application root."""


class IBazaarApplication(ILaunchpadApplication):
    """Bazaar Application"""

    all = Attribute("The full set of branches in The Bazaar")

    def getMatchingBranches():
        """Return the set of branches that match the given queries."""


class IAuthApplication(Interface):
    """Interface for AuthApplication."""

    def __getitem__(name):
        """The __getitem__ method used to traverse the app."""

    def sendPasswordChangeEmail(longurlsegment, toaddress):
        """Send an Password change special link for a user."""

    def getPersonFromDatabase(emailaddr):
        """Returns the Person in the database who has the given email address.

        If there is no Person for that email address, returns None.
        """

    def newLongURL(person):
        """Creates a new long url for the given person.

        Returns the long url segment.
        """

class IPasswordResets(IPersistent):
    """Interface for PasswordResets"""

    lifetime = Attribute("Maximum time between request and reset password")

    def newURL(person):
        """Create a new URL and store person and creation time"""

    def getPerson(long_url):
        """Get the person object using the long_url if not expired"""


class IPasswordChangeApp(Interface):
    """Interface for PasswdChangeApp."""
    code = Attribute("The transaction code")


class IPasswordEncryptor(Interface):
    """An interface representing a password encryption scheme."""

    def encrypt(plaintext):
        """Return the encrypted value of plaintext."""

    def validate(plaintext, encrypted):
        """Return a true value if the encrypted value of 'plaintext' is
        equivalent to the value of 'encrypted'.  In general, if this
        method returns true, it can also be assumed that the value of
        self.encrypt(plaintext) will compare equal to 'encrypted'.
        """


class IReadZODBAnnotation(Interface):

    def __getitem__(namespace):
        """Get the annotation for the given dotted-name namespace."""

    def get(namespace, default=None):
        """Get the annotation for the given dotted-name namespace.

        If there is no such annotation, return the default value.
        """

    def __contains__(namespace):
        """Returns true if there is an annotation with the given namespace.

        Otherwise, returns false.
        """

    def __delitem__(namespace):
        """Removes annotation at the given namespace."""


class IWriteZODBAnnotation(Interface):

    def __setitem__(namespace, value):
        """Set a value as the annotation for the given namespace."""


class IZODBAnnotation(IReadZODBAnnotation, IWriteZODBAnnotation):
    pass


class IHasOwner(Interface):
    """An object that has an owner."""

    owner = Attribute("The object's owner, which is an IPerson.")


class IHasDrivers(Interface):
    """An object that has drivers.

    Drivers have permission to approve bugs and features for specific
    distribution releases and product series.
    """
    drivers = Attribute("A list of drivers")


class IHasAppointedDriver(Interface):
    """An object that has an appointed driver."""

    driver = Choice(
        title=_("Driver"), required=False, vocabulary='ValidPersonOrTeam')


class IHasAssignee(Interface):
    """An object that has an assignee."""

    assignee = Attribute("The object's assignee, which is an IPerson.")


class IHasProduct(Interface):
    """An object that has a product attribute that is an IProduct."""

    product = Attribute("The object's product")


class IHasBug(Interface):
    """An object linked to a bug, e.g., a bugtask or a bug branch."""

    bug = Int(title=_("Bug #"))


class IHasProductAndAssignee(IHasProduct, IHasAssignee):
    """An object that has a product attribute and an assigned attribute.
    See IHasProduct and IHasAssignee."""


class IHasSecurityContact(Interface):
    """An object that has a security contact."""

    security_contact = Choice(
        title=_("Security Contact"),
        description=_(
            "The person or team who handles security-related bug reports"),
        required=False, vocabulary='ValidPersonOrTeam')


class IAging(Interface):
    """Something that gets older as time passes."""

    def currentApproximateAge():
        """Return a human-readable string of how old this thing is.

        Values returned are things like '2 minutes', '3 hours', '1 month', etc.
        """


class IHasDateCreated(Interface):
    """Something created on a certain date."""

    datecreated = Attribute("The date on which I was created.")


class IStructuralObjectPresentation(Interface):
    """Adapter that defines how a structural object is presented in the UI."""

    def getIntroHeading():
        """Any heading introduction needed (e.g. "Ubuntu source package:")."""

    def getMainHeading():
        """can be None"""

    def listChildren(num):
        """List up to num children.  Return empty string for none of these"""

    def countChildren():
        """Return the total number of children."""

    def listAltChildren(num):
        """List up to num alternative children.  Return None if alt children are not supported"""

    def countAltChildren():
        """Return the total number of alt children.  Will be called only if listAltChildren returns something."""

