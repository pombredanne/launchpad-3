from zope.schema import Text, TextLine, Field
from zope.schema.interfaces import IText, ITextLine, IField
from zope.interface import implements

from canonical.launchpad import _
from canonical.launchpad.validators import LaunchpadValidationError


# Field Interfaces

class ITitle(ITextLine):
    """A Field that implements a launchpad Title"""

class ISummary(IText):
    """A Field that implements a Summary"""

class IDescription(IText):
    """A Field that implements a Description"""

class ITimeInterval(ITextLine):
    """A field that captures a time interval in days, hours, minutes."""

class IBugField(IField):
    """A Field that allows entry of a Bug number"""


# Title
# A field to capture a launchpad object title
class Title(TextLine):
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


class StrippingTextLine(TextLine):

    def fromUnicode(self, str):
        return TextLine.fromUnicode(self, str.strip())


class ContentNameField(TextLine):
    """Base class for fields that are used by unique 'name' attributes."""
 
    errormessage = _("%s is already taken.") 

    @property
    def _content_iface(self):
        """Return the content interface. 
        
        Override this in subclasses.
        """
        return None
 
    def _getByName(self, name):
        """Return the content object with the given name.
        
        Override this in subclasses.
        """
        raise NotImplementedError
      
    def _validate(self, name):
        """Raise a LaunchpadValidationError if the name is not available.

        A name is not available if it's already in use by another object of
        this same context.
        """
        TextLine._validate(self, name)
        assert self._content_iface is not None
        if (self._content_iface.providedBy(self.context) and 
            name == getattr(self.context, self.__name__)):
            # The name wasn't changed.
            return
      
        contentobj = self._getByName(name)
        if contentobj is not None:
            raise LaunchpadValidationError(self.errormessage % name)
