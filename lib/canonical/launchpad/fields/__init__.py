# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

from zope.schema import Choice, Field, Int, Text, TextLine, Password
from zope.schema.interfaces import IPassword, IText, ITextLine, IField, IInt
from zope.interface import implements, Attribute

from canonical.launchpad import _
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.validators.name import valid_name


# Field Interfaces
class IStrippedTextLine(ITextLine):
    """A field with leading and trailing whitespaces stripped."""

class ITitle(IStrippedTextLine):
    """A Field that implements a launchpad Title"""

class ISummary(IText):
    """A Field that implements a Summary"""

class IDescription(IText):
    """A Field that implements a Description"""

class IWhiteboard(IText):
    """A Field that implements a Whiteboard"""

class ITimeInterval(ITextLine):
    """A field that captures a time interval in days, hours, minutes."""

class IBugField(IField):
    """A Field that allows entry of a Bug number or nickname"""

class IPasswordField(IPassword):
    """A field that ensures we only use http basic authentication safe
    ascii characters."""

class IShipItRecipientDisplayname(ITextLine):
    """A field used for the recipientdisplayname attribute on shipit forms.

    This is used so we can register a special widget with width constraints to
    this field. The size constraints are a requirement of the shipping company.
    """

class IShipItOrganization(ITextLine):
    """A field used for the organization attribute on shipit forms.

    This is used so we can register a special widget with width constraints to
    this field. The size constraints are a requirement of the shipping company.
    """

class IShipItCity(ITextLine):
    """A field used for the city attribute on shipit forms.

    This is used so we can register a special widget with width constraints to
    this field. The size constraints are a requirement of the shipping company.
    """

class IShipItProvince(ITextLine):
    """A field used for the province attribute on shipit forms.

    This is used so we can register a special widget with width constraints to
    this field. The size constraints are a requirement of the shipping company.
    """

class IShipItAddressline1(ITextLine):
    """A field used for the addressline1 attribute on shipit forms.

    This is used so we can register a special widget with width constraints to
    this field. The size constraints are a requirement of the shipping company.
    """

class IShipItAddressline2(ITextLine):
    """A field used for the addressline2 attribute on shipit forms.

    This is used so we can register a special widget with width constraints to
    this field. The size constraints are a requirement of the shipping company.
    """

class IShipItPhone(ITextLine):
    """A field used for the phone attribute on shipit forms.

    This is used so we can register a special widget with width constraints to
    this field. The size constraints are a requirement of the shipping company.
    """

class IShipItReason(ITextLine):
    """A field used for the reason attribute on shipit forms.

    This is used so we can register a special widget with width constraints to
    this field. The size constraints are a requirement of the shipping company.
    """

class IShipItQuantity(IInt):
    """A field used for the quantity of CDs on shipit forms."""


class ITag(ITextLine):
    """A tag.

    A text line which can be used as a simple text tag.
    """


class IUriField(ITextLine):
    """A URI.

    A text line that holds a simple
    """


class StrippedTextLine(TextLine):
    implements(IStrippedTextLine)


# Title
# A field to capture a launchpad object title
class Title(StrippedTextLine):
    implements(ITitle)


# Summary
# A field capture a Launchpad object summary
class Summary(Text):
    implements(ISummary)


# Description
# A field capture a Launchpad object description
class Description(Text):
    implements(IDescription)


# Whiteboard
# A field capture a Launchpad object whiteboard
class Whiteboard(Text):
    implements(IWhiteboard)


# TimeInterval
# A field to capture an interval in time, such as X days, Y hours, Z
# minutes.
class TimeInterval(TextLine):
    implements(ITimeInterval)

    def _validate(self, value):
        if 'mon' in value:
            return 0
        return 1


class BugField(Field):
    implements(IBugField)


class Tag(TextLine):

    implements(ITag)

    def constraint(self, value):
        """Make sure that the value is a valid name."""
        super_constraint = TextLine.constraint(self, value)
        return super_constraint and valid_name(value)


class PasswordField(Password):
    implements(IPasswordField)

    def _validate(self, value):
        # Local import to avoid circular imports
        from canonical.launchpad.interfaces.validation import valid_password
        if not valid_password(value):
            raise LaunchpadValidationError(_(
                "The password provided contains non-ASCII characters."))


class UniqueField(TextLine):
    """Base class for fields that are used for unique attributes."""

    errormessage = _("%s is already taken")
    attribute = None

    @property
    def _content_iface(self):
        """Return the content interface. 

        Override this in subclasses.
        """
        return None

    def _getByAttribute(self, input):
        """Return the content object with the given attribute.

        Override this in subclasses.
        """
        raise NotImplementedError

    def _validate(self, input):
        """Raise a LaunchpadValidationError if the attribute is not available.

        A attribute is not available if it's already in use by another object 
        of this same context. The 'input' should be valid as per TextLine.
        """
        TextLine._validate(self, input)
        assert self._content_iface is not None
        _marker = object()
        if (self._content_iface.providedBy(self.context) and 
            input == getattr(self.context, self.attribute, _marker)):
            # The attribute wasn't changed.
            return

        contentobj = self._getByAttribute(input)
        if contentobj is not None:
            raise LaunchpadValidationError(self.errormessage % input)


class ContentNameField(UniqueField):
    """Base class for fields that are used by unique 'name' attributes."""

    attribute = 'name'

    def _getByAttribute(self, name):
        """Return the content object with the given name."""
        return self._getByName(name)


class ShipItRecipientDisplayname(TextLine):
    implements(IShipItRecipientDisplayname)


class ShipItOrganization(TextLine):
    implements(IShipItOrganization)


class ShipItCity(TextLine):
    implements(IShipItCity)


class ShipItProvince(TextLine):
    implements(IShipItProvince)


class ShipItAddressline1(TextLine):
    implements(IShipItAddressline1)


class ShipItAddressline2(TextLine):
    implements(IShipItAddressline2)


class ShipItPhone(TextLine):
    implements(IShipItPhone)


class ShipItReason(Text):
    implements(IShipItReason)


class ShipItQuantity(Int):
    implements(IShipItQuantity)


class ProductBugTracker(Choice):
    """A bug tracker used by a Product.

    It accepts all the values in the vocabulary, as well as a special
    marker object, which represents the Malone bug tracker.
    This field uses two attributes to model its state, 'official_malone'
    and 'bugtracker'
    """
    malone_marker = object()

    def get(self, ob):
        if ob.official_malone:
            return self.malone_marker
        else:
            return ob.bugtracker

    def set(self, ob, value):
        if self.readonly:
            raise TypeError("Can't set values on read-only fields.")
        if value is self.malone_marker:
            ob.official_malone = True
            ob.bugtracker = None
        else:
            ob.official_malone = False
            ob.bugtracker = value


class UriField(TextLine):
    implements(IUriField)

    def __init__(self, allowed_schemes=(), allow_userinfo=True,
                 allow_port=True, allow_query=True, allow_fragment=True,
                 trailing_slash=None, **kwargs):
        super(UriField, self).__init__(**kwargs)
        self.allowed_schemes = set(allowed_schemes)
        self.allow_userinfo = allow_userinfo
        self.allow_port = allow_port
        self.allow_query = allow_query
        self.allow_fragment = allow_fragment
        self.trailing_slash = trailing_slash

    def _validate(self, value):
        super(UriField, self)._validate(value)

        # Local import to avoid circular imports:
        from canonical.launchpad.webapp.uri import Uri, InvalidUriError
        try:
            uri = Uri(value)
        except InvalidUriError, e:
            raise LaunchpadValidationError(str(e))
        
        if self.allowed_schemes and uri.scheme not in self.allowed_schemes:
            raise LaunchpadValidationError(
                'The URI scheme "%s" is not allowed.  Only URIs with '
                'the following schemes may be used: %s'
                % (uri.scheme, ', '.join(sorted(self.allowed_schemes))))

        if not self.allow_userinfo and uri.userinfo is not None:
            raise LaunchpadValidationError(
                'A username may not be specified in the URI.')

        if not self.allow_port and uri.port is not None:
            raise LaunchpadValidationError(
                'Non-default ports are not allowed.')

        if not self.allow_query and uri.query is not None:
            raise LaunchpadValidationError(
                'URIs with query strings are not allowed.')

        if not self.allow_fragment and uri.fragment is not None:
            raise LaunchpadValidationError(
                'URIs with fragment identifiers are not allowed.')

        if self.trailing_slash is not None:
            has_slash = uri.path.endswith('/')
            if self.trailing_slash:
                if uri.path.endswith('/'):
                    raise LaunchpadValidationError(
                        'The URI must end with a slash.')
            else:
                # Empty paths are normalised to a single slash, so
                # allow that.
                if uri.path != '/' and uri.path.endswith('/'):
                    raise LaunchpadValidationError(
                        'The URI must not end with a slash.')
