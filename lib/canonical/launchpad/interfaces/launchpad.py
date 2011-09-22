# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213,W0611
# XXX Aaron Bentley 2008-01-24: See comment from kiko re:import shims

"""Interfaces pertaining to the launchpad application.

Note that these are not interfaces to application content objects.
"""
__metaclass__ = type

from lazr.restful.interfaces import IServiceRootResource
from persistent import IPersistent
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Choice,
    Int,
    TextLine,
    )

from canonical.launchpad import _
# XXX kiko 2007-02-08:
# These import shims are actually necessary if we don't go over the
# entire codebase and fix where the import should come from.
from canonical.launchpad.webapp.interfaces import (
    IBasicLaunchpadRequest,
    ILaunchBag,
    ILaunchpadApplication,
    ILaunchpadRoot,
    IOpenLaunchBag,
    UnsafeFormGetSubmissionError,
    )


__all__ = [
    'IAging',
    'IAppFrontPageSearchForm',
    'IAuthApplication',
    'IAuthServerApplication',
    'IBasicLaunchpadRequest',
    'IBazaarApplication',
    'IFeedsApplication',
    'IHasAssignee',
    'IHasBug',
    'IHasDateCreated',
    'IHasExternalBugTracker',
    'IHasIcon',
    'IHasLogo',
    'IHasMugshot',
    'IHasProduct',
    'IHasProductAndAssignee',
    'ILaunchBag',
    'ILaunchpadRoot',
    'INotificationRecipientSet',
    'IOpenLaunchBag',
    'IPasswordChangeApp',
    'IPasswordEncryptor',
    'IPasswordResets',
    'IPrivateApplication',
    'IPrivateMaloneApplication',
    'IPrivacy',
    'IReadZODBAnnotation',
    'IRosettaApplication',
    'IWebServiceApplication',
    'IWriteZODBAnnotation',
    'IZODBAnnotation',
    'NameNotAvailable',
    'UnknownRecipientError',
    'UnsafeFormGetSubmissionError',
    ]


class NameNotAvailable(KeyError):
    """You're trying to set a name, but the name you chose isn't available."""


class IHasExternalBugTracker(Interface):
    """An object that can have an external bugtracker specified."""

    def getExternalBugTracker():
        """Return the external bug tracker used by this bug tracker.

        If the product uses Launchpad, return None.

        If the product doesn't have a bug tracker specified, return the
        project bug tracker instead. If the product doesn't belong to a
        superproject, or if the superproject doesn't have a bug tracker,
        return None.
        """


class IPrivateMaloneApplication(ILaunchpadApplication):
    """Private application root for malone."""


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


class IBazaarApplication(ILaunchpadApplication):
    """Bazaar Application"""


class IPrivateApplication(ILaunchpadApplication):
    """Launchpad private XML-RPC application root."""

    authserver = Attribute("""Old Authserver API end point.""")

    codeimportscheduler = Attribute("""Code import scheduler end point.""")

    codehosting = Attribute("""Codehosting end point.""")

    mailinglists = Attribute("""Mailing list XML-RPC end point.""")

    bugs = Attribute("""Launchpad Bugs XML-RPC end point.""")

    softwarecenteragent = Attribute(
        """Software center agent XML-RPC end point.""")


class IAuthServerApplication(ILaunchpadApplication):
    """Launchpad legacy AuthServer application root."""


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


class IFeedsApplication(ILaunchpadApplication):
    """Launchpad Feeds application root."""


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


class IWebServiceApplication(ILaunchpadApplication, IServiceRootResource):
    """Launchpad web service application root."""


class IWriteZODBAnnotation(Interface):

    def __setitem__(namespace, value):
        """Set a value as the annotation for the given namespace."""


class IZODBAnnotation(IReadZODBAnnotation, IWriteZODBAnnotation):
    pass


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

        Values returned are things like '2 minutes', '3 hours',
        '1 month', etc.
        """


class IPrivacy(Interface):
    """Something that can be private."""

    private = Bool(
        title=_("This is private"),
        required=False,
        description=_(
            "Private objects are visible to members or subscribers."))


class IHasDateCreated(Interface):
    """Something created on a certain date."""

    datecreated = Attribute("The date on which I was created.")


class IAppFrontPageSearchForm(Interface):
    """Schema for the app-specific front page search question forms."""

    search_text = TextLine(title=_('Search text'), required=False)

    scope = Choice(title=_('Search scope'), required=False,
                   vocabulary='DistributionOrProductOrProjectGroup')


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

    def getRecipientPersons():
        """Return the set of individual Persons who will be notified.

        :return: An iterator of (`email_address`, `IPerson`), unsorted.
        """

    def __iter__():
        """Return an iterator of the recipients."""

    def __contains__(person_or_email):
        """Is person_or_email in the notification recipients list?

        Return true if person or email is in the notification recipients list.
        """

    def __nonzero__():
        """Return False when the set is empty, True when it's not."""

    def getReason(person_or_email):
        """Return a reason tuple containing (text, header) for an address.

        The text is meant to appear in the notification footer. The header
        should be a short code that will appear in an
        X-Launchpad-Message-Rationale header for automatic filtering.

        :param person_or_email: An `IPerson` or email address that is in the
            recipients list.

        :raises UnknownRecipientError: if the person or email isn't in the
            recipients list.
        """

    def add(person, reason, header):
        """Add a person or a sequence of persons to the recipients list.

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

    def remove(person):
        """Remove a person or a list of persons from the recipients list.

        :param person: The `IPerson` or a sequence of `IPerson`
            that will removed from the recipients list.
        """

    def update(recipient_set):
        """Updates this instance's reasons with reasons from another set.

        The rationale for recipient already in this set will not be updated.

        :param recipient_set: An `INotificationRecipientSet`.
        """
