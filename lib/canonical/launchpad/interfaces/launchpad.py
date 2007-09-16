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
from zope.schema import Choice, Int, TextLine
from persistent import IPersistent

from canonical.launchpad import _
from canonical.launchpad.webapp.interfaces import ILaunchpadApplication

# XXX kiko 2007-02-08:
# These import shims are actually necessary if we don't go over the
# entire codebase and fix where the import should come from.
from canonical.launchpad.webapp.interfaces import (
    NotFoundError, ILaunchpadRoot, ILaunchBag, IOpenLaunchBag, IBreadcrumb,
    IBasicLaunchpadRequest, IAfterTraverseEvent, AfterTraverseEvent,
    IBeforeTraverseEvent, BeforeTraverseEvent, UnexpectedFormData,
    UnsafeFormGetSubmissionError,
    )

__all__ = [
    'AfterTraverseEvent',
    'BeforeTraverseEvent',
    'IAfterTraverseEvent',
    'IAging',
    'IAppFrontPageSearchForm',
    'IAuthApplication',
    'IBasicLaunchpadRequest',
    'IBazaarApplication',
    'IBeforeTraverseEvent',
    'IBreadcrumb',
    'ICrowd',
    'IHasAppointedDriver',
    'IHasAssignee',
    'IHasBug',
    'IHasDateCreated',
    'IHasDrivers',
    'IHasIcon',
    'IHasLogo',
    'IHasMugshot',
    'IHasOwner',
    'IHasProduct',
    'IHasProductAndAssignee',
    'IHasSecurityContact',
    'ILaunchBag',
    'ILaunchpadCelebrities',
    'ILaunchpadRoot',
    'IMaloneApplication',
    'INotificationRecipientSet',
    'IOpenIdApplication',
    'IOpenLaunchBag',
    'IPasswordChangeApp',
    'IPasswordEncryptor',
    'IPasswordResets',
    'IPrivateApplication',
    'IReadZODBAnnotation',
    'IRegistryApplication',
    'IRosettaApplication',
    'IShipItApplication',
    'IStructuralHeaderPresentation',
    'IStructuralObjectPresentation',
    'IWriteZODBAnnotation',
    'IZODBAnnotation',
    'NameNotAvailable',
    'NotFoundError',
    'UnexpectedFormData',
    'UnknownRecipientError',
    'UnsafeFormGetSubmissionError',
    ]


class NameNotAvailable(KeyError):
    """You're trying to set a name, but the name you chose is not available."""


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
    launchpad = Attribute("The Launchpad project.")
    janitor = Attribute("The Launchpad Janitor.")
    launchpad_beta_testers = Attribute("The Launchpad Beta Testers team.")
    ubuntu_archive_mirror = Attribute("The main archive mirror for Ubuntu.")
    ubuntu_cdimage_mirror = Attribute("The main cdimage mirror for Ubuntu.")


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

    def searchTasks(search_params):
        """Search IBugTasks with the given search parameters."""

    bug_count = Attribute("The number of bugs recorded in Launchpad")
    bugwatch_count = Attribute("The number of links to external bug trackers")
    bugextref_count = Attribute("The number of links to outside URL's")
    bugtask_count = Attribute("The number of bug tasks in Launchpad")
    projects_with_bugs_count = Attribute("The number of products and "
        "distributions which have bugs in Launchpad.")
    shared_bug_count = Attribute("The number of bugs that span multiple "
        "products and distributions")
    bugtracker_count = Attribute("The number of bug trackers in Launchpad")
    top_bugtrackers = Attribute("The BugTrackers with the most watches.")
    latest_bugs = Attribute("The latest 5 bugs filed.")


class IRosettaApplication(ILaunchpadApplication):
    """Application root for rosetta."""

    languages = Attribute(
        'Languages Launchpad can translate into.')
    language_count = Attribute(
        'Number of languages Launchpad can translate into.')
    statsdate = Attribute('The date stats were last updated.')
    translation_groups = Attribute('ITranslationGroupSet object.')

    def translatable_products():
        """Return a list of the translatable products."""

    def featured_products():
        """Return a sample of all the translatable products."""

    def translatable_distroseriess():
        """Return a list of the distroseriess in launchpad for which
        translations can be done.
        """

    def potemplate_count():
        """Return the number of potemplates in the system."""

    def pofile_count():
        """Return the number of pofiles in the system."""

    def pomsgid_count():
        """Return the number of msgs in the system."""

    def translator_count():
        """Return the number of people who have given translations."""


class IRegistryApplication(ILaunchpadApplication):
    """Registry application root."""


class IShipItApplication(ILaunchpadApplication):
    """ShipIt application root."""


class IBazaarApplication(ILaunchpadApplication):
    """Bazaar Application"""


class IOpenIdApplication(ILaunchpadApplication):
    """Launchpad Login Service application root."""


class IPrivateApplication(ILaunchpadApplication):
    """Launchpad private XML-RPC application root."""

    mailinglists = Attribute("""Mailing list XML-RPC end point.""")


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
    series.
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


class IHasIcon(Interface):
    """An object that can have a custom icon."""

    # Each of the objects that implements this needs a custom schema, so
    # here we can just use Attributes
    icon = Attribute("The 14x14 icon.")


class IHasLogo(Interface):
    """An object that can have a custom logo."""

    # Each of the objects that implements this needs a custom schema, so
    # here we can just use Attributes
    logo = Attribute("The 64x64 logo.")


class IHasMugshot(Interface):
    """An object that can have a custom mugshot."""

    # Each of the objects that implements this needs a custom schema, so
    # here we can just use Attributes
    mugshot = Attribute("The 192x192 mugshot.")


class IAging(Interface):
    """Something that gets older as time passes."""

    def currentApproximateAge():
        """Return a human-readable string of how old this thing is.

        Values returned are things like '2 minutes', '3 hours', '1 month', etc.
        """


class IHasDateCreated(Interface):
    """Something created on a certain date."""

    datecreated = Attribute("The date on which I was created.")


class IStructuralHeaderPresentation(Interface):
    """Adapter for common aspects of a structural object's presentation."""

    def isPrivate():
        """Whether read access to the object is restricted."""

    def getIntroHeading():
        """Any heading introduction needed (e.g. "Ubuntu source package:")."""

    def getMainHeading():
        """can be None"""


class IStructuralObjectPresentation(IStructuralHeaderPresentation):
    """Adapter for less common aspects of a structural object's presentation."""

    def listChildren(num):
        """List up to num children.  Return empty string for none of these"""

    def countChildren():
        """Return the total number of children."""

    def listAltChildren(num):
        """List up to num alternative children.  Return None if alt children are not supported"""

    def countAltChildren():
        """Return the total number of alt children.  Will be called only if listAltChildren returns something."""


class IAppFrontPageSearchForm(Interface):
    """Schema for the app-specific front page search question forms."""

    search_text = TextLine(title=_('Search text'), required=False)

    scope = Choice(title=_('Search scope'), required=False,
                   vocabulary='DistributionOrProductOrProject')


class UnknownRecipientError(KeyError):
    """Error raised when an email or person isn't part of the recipient set.
    """


class INotificationRecipientSet(Interface):
    """Represents a set of notification recipients and rationales.

    All Launchpad emails should include a footer explaining why the user
    is receiving the email. An INotificationRecipientSet encapsulates a
    list of recipients along the rationale for being on the recipients list.

    The pattern for using this are as follows: email addresses in an
    INotificationRecipientSet are being notified because of a specific
    event (for instance, because a bug changed). The rationales describe
    why that email addresses is included in the recipient list,
    detailing subscription types, membership in teams and/or other
    possible reasons.

    The set maintains the list of `IPerson` that will be contacted as well
    as the email address to use to contact them.
    """
    def getEmails():
        """Return all email addresses registered, sorted alphabetically."""

    def getRecipients():
        """Return the set of person who will be notified.

        :return: An iterator of `IPerson`, sorted by display name.
        """

    def __iter__():
        """Return an iterator of the recipients."""

    def __contains__(person_or_email):
        """Return true if person or email is in the notification recipients list."""

    def __nonzero__():
        """Return False when the set is empty, True when it's not."""

    def getReason(person_or_email):
        """Return a reason tuple containing (text, header) for an address.

        The text is meant to appear in the notification footer. The header
        should be a short code that will appear in an
        X-Launchpad-Message-Rationale header for automatic filtering.

        :param person_or_email: An `IPerson` or email adress that is in the
            recipients list.

        :raises UnknownRecipientError: if the person or email isn't in the
            recipients list.
        """

    def add(person, reason, header):
        """Add a person or sequence of person to the recipients list.

        When the added person is a team without an email address, all its
        members emails will be added. If the person is already in the
        recipients list, the reson for contacting him is not changed.

        :param person: The `IPerson` or a sequence of `IPerson`
            that will be notified.
        :param reason: The rationale message that should appear in the
            notification footer.
        :param header: The code that will appear in the
            X-Launchpad-Message-Rationale header.
        """

    def update(recipient_set):
        """Updates this instance's reasons with reasons from another set.

        The rationale for recipient already in this set will not be updated.

        :param recipient_set: An `INotificationRecipientSet`.
        """
