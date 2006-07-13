# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

from zope.schema import Password, Text, TextLine, Field, Int
from zope.schema.interfaces import IPassword, IText, ITextLine, IField, IInt
from zope.interface import implements, Attribute

from canonical.launchpad import _
from canonical.launchpad.validators import LaunchpadValidationError


# Field Interfaces
class IStrippedTextLine(ITextLine):
    """A field with leading and trailing whitespaces stripped."""

class ITitle(IStrippedTextLine):
    """A Field that implements a launchpad Title"""

class ISummary(IText):
    """A Field that implements a Summary"""

class IDescription(IText):
    """A Field that implements a Description"""

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


class IBugTag(ITextLine):
    """A bug tag.

    A text line which doesn't contain any space characters.
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


class BugTag(TextLine):

    implements(IBugTag)

    def constraint(self, value):
        if ' ' in value:
            return False
        else:
            return TextLine.constraint(self, value)


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

