# Monkeypatch sqlobject to add __len__ to SelectResults.
import sqlobject.main
if getattr(sqlobject.main.SelectResults, '__len__', None) is None:
    sqlobject.main.SelectResults.__len__ = lambda self: self.count()

#
# first the real ones
#
from canonical.launchpad.database.milestone import *
from canonical.launchpad.database.person import *
from canonical.launchpad.database.product import *
from canonical.launchpad.database.productseries import *
from canonical.launchpad.database.productrelease import *
from canonical.launchpad.database.project import *
from canonical.launchpad.database.bug import *
from canonical.launchpad.database.bugassignment import *
from canonical.launchpad.database.bugwatch import *
from canonical.launchpad.database.bugsubscription import *
from canonical.launchpad.database.bugmessage import *
from canonical.launchpad.database.bugactivity import *
from canonical.launchpad.database.bugattachment import *
from canonical.launchpad.database.bugextref import *
from canonical.launchpad.database.cveref import *
from canonical.launchpad.database.bugtracker import *
from canonical.launchpad.database.sourcesource import *
from canonical.launchpad.database.pofile import *
from canonical.launchpad.database.archarchive import *
from canonical.launchpad.database.archbranch import *
from canonical.launchpad.database.archchangeset import *
from canonical.launchpad.database.librarian import *
from canonical.launchpad.database.infestation import *
from canonical.launchpad.database.sourcepackage import *
from canonical.launchpad.database.binarypackage import *
from canonical.launchpad.database.publishedpackage import *
from canonical.launchpad.database.distribution import *
from canonical.launchpad.database.distrorelease import *
from canonical.launchpad.database.person import *
from canonical.launchpad.database.schema import *
from canonical.launchpad.database.language import *
from canonical.launchpad.database.translation_effort import *
from canonical.launchpad.database.processor import *
from canonical.launchpad.database.manifest import *
from canonical.launchpad.database.manifestentry import *
from canonical.launchpad.database.branch import *
from canonical.launchpad.database.build import *
from canonical.launchpad.database.publishing import *
from canonical.launchpad.database.files import *
from canonical.launchpad.database.bounty import *
from canonical.launchpad.database.message import *
from canonical.launchpad.database.queue import *
from canonical.launchpad.database.country import *
from canonical.launchpad.database.spokenin import *
from canonical.launchpad.database.cal import *

# XXX old style file with all the Soyuz classes in it that still need to br
# broken out.
from canonical.launchpad.database.soyuz import *

