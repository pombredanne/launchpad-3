# Copyright 2004-2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,W0401

__metaclass__ = type
__all__ = [
    'AnnouncementDate',
    'BaseImageUpload',
    'BlacklistableContentNameField',
    'BugField',
    'ContentNameField',
    'Description',
    'DuplicateBug',
    'FieldNotBoundError',
    'IAnnouncementDate',
    'IBaseImageUpload',
    'IBugField',
    'IDescription',
    'IPasswordField',
    'IShipItAddressline1',
    'IShipItAddressline2',
    'IShipItCity',
    'IShipItOrganization',
    'IShipItPhone',
    'IShipItProvince',
    'IShipItQuantity',
    'IShipItReason',
    'IShipItRecipientDisplayname',
    'IStrippedTextLine',
    'ISummary',
    'ITag',
    'ITimeInterval',
    'ITitle',
    'IURIField',
    'IWhiteboard',
    'IconImageUpload',
    'is_valid_public_person_link',
    'KEEP_SAME_IMAGE',
    'LogoImageUpload',
    'MugshotImageUpload',
    'PasswordField',
    'PillarNameField',
    'ProductBugTracker',
    'ProductNameField',
    'PublicPersonChoice',
    'ShipItAddressline1',
    'ShipItAddressline2',
    'ShipItCity',
    'ShipItOrganization',
    'ShipItPhone',
    'ShipItProvince',
    'ShipItQuantity',
    'ShipItReason',
    'ShipItRecipientDisplayname',
    'StrippedTextLine',
    'Summary',
    'Tag',
    'TimeInterval',
    'Title',
    'URIField',
    'UniqueField',
    'Whiteboard',
    ]


from StringIO import StringIO
from textwrap import dedent

from zope.component import getUtility
from zope.schema import (
    Bool, Bytes, Choice, Datetime, Int, Password, Text, TextLine,
    Tuple)
from zope.schema.interfaces import (
    ConstraintNotSatisfied, IBytes, IDatetime, IInt, IObject, IPassword,
    IText, ITextLine, Interface)
from zope.interface import implements
from zope.security.interfaces import ForbiddenAttribute

from canonical.launchpad import _
from canonical.launchpad.interfaces.pillar import IPillarNameSet
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.validators.name import valid_name, name_validator
from canonical.lazr.rest.schema import Reference
from canonical.foaf import nickname


# Marker object to tell BaseImageUpload to keep the existing image.
KEEP_SAME_IMAGE = object()


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

class IBugField(IObject):
    """A field that allows entry of a Bug number or nickname"""

class IPasswordField(IPassword):
    """A field that ensures we only use http basic authentication safe
    ascii characters."""

class IAnnouncementDate(IDatetime):
    """Marker interface for AnnouncementDate fields.

    This is used in cases where we either want to publish something
    immediately, or come back in future to publish it, or set a date for
    publication in advance. Essentially this amounts to a Datetime that can
    be None.
    """

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


class IURIField(ITextLine):
    """A URI.

    A text line that holds a URI.
    """
    trailing_slash = Bool(
        title=_('Whether a trailing slash is required for this field'),
        required=False,
        description=_('If set to True, then the path component of the URI '
                      'must end in a slash.  If set to False, then the path '
                      'component must not end in a slash.  If set to None, '
                      'then no check is performed.'))


class IBaseImageUpload(IBytes):
    """Marker interface for ImageUpload fields."""

    dimensions = Tuple(
        title=_('Maximum dimensions'),
        description=_('A two-tuple with the maximum width and height (in '
                      'pixels) of this image.'))
    max_size = Int(
        title=_('Maximum size'),
        description=_('The maximum size (in bytes) of this image.'))

    default_image_resource = TextLine(
        title=_('The default image'),
        description=_(
            'The URL of the zope3 resource of the default image that should '
            'be used. Something of the form /@@/nyet-mugshot'))

    def getCurrentImage():
        """Return the value of the field for the object bound to it.

        Raise FieldNotBoundError if the field is not bound to any object.
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


class AnnouncementDate(Datetime):
    implements(IDatetime)


# TimeInterval
# A field to capture an interval in time, such as X days, Y hours, Z
# minutes.
class TimeInterval(TextLine):
    implements(ITimeInterval)

    def _validate(self, value):
        if 'mon' in value:
            return 0
        return 1


class BugField(Reference):
    implements(IBugField)

    def __init__(self, *args, **kwargs):
        """The schema will always be `IBug`."""
        super(BugField, self).__init__(Interface, *args, **kwargs)

    def _get_schema(self):
        """Get the schema here to avoid circular imports."""
        from canonical.launchpad.interfaces import IBug
        return IBug

    def _set_schema(self, schema):
        """Ignore attempts to set the schema by the superclass."""

    schema = property(_get_schema, _set_schema)


class DuplicateBug(BugField):
    """A bug that the context is a duplicate of."""

    def _validate(self, value):
        """Prevent dups of dups.

        Returns True if the dup target is not a duplicate /and/ if the
        current bug doesn't have any duplicates referencing it /and/ if the
        bug isn't a duplicate of itself, otherwise
        return False.
        """
        from canonical.launchpad.interfaces.bug import IBugSet
        bugset = getUtility(IBugSet)
        current_bug = self.context
        dup_target = value
        current_bug_has_dup_refs = bool(bugset.searchAsUser(
            user=getUtility(ILaunchBag).user, duplicateof=current_bug))
        if current_bug == dup_target:
            raise LaunchpadValidationError(_(dedent("""
                You can't mark a bug as a duplicate of itself.""")))
        elif dup_target.duplicateof is not None:
            raise LaunchpadValidationError(_(dedent("""
                Bug ${dup} is already a duplicate of bug ${orig}. You
                can only mark a bug report as duplicate of one that
                isn't a duplicate itself.
                """), mapping={'dup': dup_target.id,
                               'orig': dup_target.duplicateof.id}))
        elif current_bug_has_dup_refs:
            raise LaunchpadValidationError(_(dedent("""
                There are other bugs already marked as duplicates of
                Bug ${current}.  These bugs should be changed to be
                duplicates of another bug if you are certain you would
                like to perform this change."""),
                mapping={'current': current_bug.id}))
        else:
            return True


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

    def _isValueTaken(self, value):
        """Returns true if and only if the specified value is already taken.
        """
        return self._getByAttribute(value) is not None

    def _validate(self, input):
        """Raise a LaunchpadValidationError if the attribute is not available.

        A attribute is not available if it's already in use by another
        object of this same context. The 'input' should be valid as per
        TextLine.
        """
        super(UniqueField, self)._validate(input)
        assert self._content_iface is not None
        _marker = object()

        # If we are editing an existing object and the attribute is
        # unchanged...
        if (self._content_iface.providedBy(self.context) and
            input == getattr(self.context, self.attribute, _marker)):
            # ...then do nothing: we already know the value is unique.
            return

        # Now we know we are dealing with either a new object, or an
        # object whose attribute is going to be updated. We need to
        # ensure the new value is unique.
        if self._isValueTaken(input):
            raise LaunchpadValidationError(self.errormessage % input)


class ContentNameField(UniqueField):
    """Base class for fields that are used by unique 'name' attributes."""

    attribute = 'name'

    def _getByAttribute(self, name):
        """Return the content object with the given name."""
        return self._getByName(name)

    def _validate(self, name):
        """Check that the given name is valid (and by delegation, unique)."""
        name_validator(name)
        UniqueField._validate(self, name)


class BlacklistableContentNameField(ContentNameField):
    """ContentNameField that also need to check against the NameBlacklist
       table in case the name has been blacklisted.
    """
    def _validate(self, input):
        """As per UniqueField._validate, except a LaunchpadValidationError
           is also raised if the name has been blacklisted.
        """
        super(BlacklistableContentNameField, self)._validate(input)

        _marker = object()
        if (self._content_iface.providedBy(self.context) and
            input == getattr(self.context, self.attribute, _marker)):
            # The attribute wasn't changed.
            return

        if nickname.is_blacklisted(name=input):
            raise LaunchpadValidationError(
                    "The name '%s' has been blocked by the "
                    "Launchpad administrators" % input
                    )


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


class URIField(TextLine):
    implements(IURIField)

    def __init__(self, allowed_schemes=(), allow_userinfo=True,
                 allow_port=True, allow_query=True, allow_fragment=True,
                 trailing_slash=None, **kwargs):
        super(URIField, self).__init__(**kwargs)
        self.allowed_schemes = set(allowed_schemes)
        self.allow_userinfo = allow_userinfo
        self.allow_port = allow_port
        self.allow_query = allow_query
        self.allow_fragment = allow_fragment
        self.trailing_slash = trailing_slash

    def _validate(self, value):
        super(URIField, self)._validate(value)

        # Local import to avoid circular imports:
        from canonical.launchpad.webapp.uri import URI, InvalidURIError
        try:
            uri = URI(value)
        except InvalidURIError, e:
            raise LaunchpadValidationError(e)

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
                if not has_slash:
                    raise LaunchpadValidationError(
                        'The URI must end with a slash.')
            else:
                # Empty paths are normalised to a single slash, so
                # allow that.
                if uri.path != '/' and has_slash:
                    raise LaunchpadValidationError(
                        'The URI must not end with a slash.')


class FieldNotBoundError(Exception):
    """The field is not bound to any object."""


class BaseImageUpload(Bytes):
    """Base class for ImageUpload fields.

    Any subclass of this one must be used in conjunction with
    ImageUploadWidget and must define the following attributes:
    - dimensions: the exact dimensions of the image; a tuple of the
      form (width, height).
    - max_size: the maximum size of the image, in bytes.
    """

    implements(IBaseImageUpload)

    exact_dimensions = True
    dimensions = ()
    max_size = 0

    def __init__(self, default_image_resource='/@@/nyet-icon', **kw):
        self.default_image_resource = default_image_resource
        Bytes.__init__(self, **kw)

    def getCurrentImage(self):
        if self.context is None:
            raise FieldNotBoundError("This field must be bound to an object.")
        else:
            try:
                current = getattr(self.context, self.__name__)
            except ForbiddenAttribute:
                # When this field is used in add forms it gets bound to
                # I*Set objects, which don't have the attribute represented
                # by the field, so we need this hack here.
                current = None
            return current

    def _valid_image(self, image):
        """Check that the given image is under the given constraints."""
        # No global import to avoid hard dependency on PIL being installed
        import PIL.Image
        if len(image) > self.max_size:
            raise LaunchpadValidationError(_(dedent("""
                This image exceeds the maximum allowed size in bytes.""")))
        try:
            pil_image = PIL.Image.open(StringIO(image))
        except IOError:
            raise LaunchpadValidationError(_(dedent("""
                The file uploaded was not recognized as an image; please
                check it and retry.""")))
        width, height = pil_image.size
        required_width, required_height = self.dimensions
        if self.exact_dimensions:
            if width != required_width or height != required_height:
                raise LaunchpadValidationError(_(dedent("""
                    This image is not exactly ${width}x${height}
                    pixels in size."""),
                    mapping={'width': required_width,
                             'height': required_height}))
        else:
            if width > required_width or height > required_height:
                raise LaunchpadValidationError(_(dedent("""
                    This image is larger than ${width}x${height}
                    pixels in size."""),
                    mapping={'width': required_width,
                             'height': required_height}))
        return True

    def _validate(self, value):
        if hasattr(value, 'seek'):
            value.seek(0)
            content = value.read()
        else:
            content = value
        super(BaseImageUpload, self)._validate(content)
        self._valid_image(content)

    def set(self, object, value):
        if value is not KEEP_SAME_IMAGE:
            Bytes.set(self, object, value)


class IconImageUpload(BaseImageUpload):

    dimensions = (14, 14)
    max_size = 5*1024
    default_image_resource = '/@@/nyet-icon'


class LogoImageUpload(BaseImageUpload):

    dimensions = (64, 64)
    max_size = 50*1024
    default_image_resource = '/@@/nyet-logo'


class MugshotImageUpload(BaseImageUpload):

    dimensions = (192, 192)
    max_size = 100*1024
    default_image_resource = '/@@/nyet-mugshot'


class PillarNameField(BlacklistableContentNameField):
    """Base field used for names of distros/projects/products."""

    errormessage = _("%s is already used by another project")

    def _getByName(self, name):
        return getUtility(IPillarNameSet).getByName(name)


class ProductNameField(PillarNameField):
    """Field used by IProduct.name."""

    @property
    def _content_iface(self):
        # Local import to avoid circular dependencies.
        from canonical.launchpad.interfaces.product import IProduct
        return IProduct


def is_valid_public_person_link(person, other):
    from canonical.launchpad.interfaces import IPerson, PersonVisibility
    if not IPerson.providedBy(person):
        raise ConstraintNotSatisfied("Expected a person.")
    if person.visibility == PersonVisibility.PUBLIC:
        return True
    else:
        return False


class PublicPersonChoice(Choice):
    def constraint(self, value):
        return is_valid_public_person_link(value, self.context)
