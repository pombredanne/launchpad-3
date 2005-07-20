"""
Vocabularies. Note that you probably shouldn't be importing stuff from these
modules, as it is better to have your Schemas fields look up the vocabularies
by name. Some of these vocabularies will only work if looked up by name,
as they require context to calculare the available options. It also
avoids circular import issues.

eg.

class IFoo(Interface):
    thingy = Choice(..., vocabulary='Thingies')

The binding of name -> class is done in the configure.zcml

"""

from canonical.launchpad.vocabularies.dbschema import *
from canonical.launchpad.vocabularies.dbobjects import *
from canonical.launchpad.vocabularies.timezones import *
