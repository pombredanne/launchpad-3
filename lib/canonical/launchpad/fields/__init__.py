
from zope.schema import Text, TextLine

# Summary
# A field capture a Launchpad object summary
class Summary(Text):
    pass


# Title
# A field to capture a launchpad object title
class Title(TextLine):
    pass

