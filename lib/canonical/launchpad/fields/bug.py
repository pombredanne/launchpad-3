
from zope.schema import Text
from zope.schema.interfaces import IText

# BugSummary
# A field capture a bug summary
class BugSummary(Text):

    def _validate(self, value):
        pass

