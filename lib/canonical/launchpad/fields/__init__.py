
from zope.schema import Text, TextLine
from zope.schema.interfaces import IText, ITextLine
from zope.interface import implements, classImplements

import datetime

# Field Interfaces

class ISummary(IText):
    """A Field that implements a Bug Summary"""

class ITitle(ITextLine):
    """A Field that implements a launchpad Title"""

class ITimeInterval(ITextLine):
    """A field that captures a time interval in days, hours, minutes."""

# Summary
# A field capture a Launchpad object summary
class Summary(Text):
    implements(ISummary)


# Title
# A field to capture a launchpad object title
class Title(TextLine):
    implements(ITitle)


# TimeInterval
# A field to capture an interval in time, such as X days, Y hours, Z
# minutes.
class TimeInterval(TextLine):
    implements(ITimeInterval)

    def _validate(self, value):
        if 'mon' in value:
            return 0
        return 1

