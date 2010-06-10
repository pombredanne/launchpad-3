# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0401,C0301

__metaclass__ = type

# This module is deprecated. Do not add to this. Do not import from this.

# XXX sinzui 2010-06-09: shipit requires these glob imports.
from canonical.launchpad.interfaces.lpstorm import (
    IMasterObject, ISlaveStore, IStore)
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.webapp.interfaces import ILaunchBag, ILaunchpadRoot
from lp.registry.interfaces.person import IPersonSet

# XXX sinzui 2010-06-09: These appear to be needed for WADL generation.
from lp.registry.interfaces.distributionsourcepackage import *
from canonical.launchpad.interfaces.emailaddress import *
from canonical.launchpad.interfaces.message import *
from canonical.launchpad.interfaces.launchpad import *

from lp.registry.interfaces.person import *
from lp.registry.interfaces.pillar import *
from lp.registry.interfaces.commercialsubscription import *
from lp.registry.interfaces.distribution import *
from lp.registry.interfaces.distributionmirror import *
from lp.registry.interfaces.distroseries import *
from lp.registry.interfaces.gpg import *
from lp.registry.interfaces.irc import *
from lp.registry.interfaces.jabber import *
from lp.registry.interfaces.mailinglist import *
from lp.registry.interfaces.milestone import *
from lp.registry.interfaces.product import *
from lp.registry.interfaces.productrelease import *
from lp.registry.interfaces.productseries import *
from lp.registry.interfaces.projectgroup import *
from lp.registry.interfaces.ssh import *
from lp.registry.interfaces.structuralsubscription import *
from lp.registry.interfaces.teammembership import *
from lp.registry.interfaces.wikiname import *

from lp.hardwaredb.interfaces.hwdb import *

from lp.bugs.interfaces.bugactivity import *
from lp.bugs.interfaces.bugattachment import *
from lp.bugs.interfaces.bug import *
from lp.bugs.interfaces.bugbranch import *
from lp.bugs.interfaces.bugcve import *
from lp.bugs.interfaces.buglink import *
from lp.bugs.interfaces.bugmessage import *
from lp.bugs.interfaces.bugnomination import *
from lp.bugs.interfaces.bugnotification import *
from lp.bugs.interfaces.bugsubscription import *
from lp.bugs.interfaces.bugsupervisor import *
from lp.bugs.interfaces.bugtask import *
from lp.bugs.interfaces.bugtarget import *
from lp.bugs.interfaces.bugtracker import *
from lp.bugs.interfaces.bugwatch import *
from lp.bugs.interfaces.cve import *
from lp.bugs.interfaces.cvereference import *
from lp.bugs.interfaces.externalbugtracker import *

from lp.buildmaster.interfaces.builder import *
from lp.soyuz.interfaces.archive import *
from lp.soyuz.interfaces.archivedependency import *
from lp.soyuz.interfaces.archivepermission import *
from lp.soyuz.interfaces.archivesubscriber import *
from lp.soyuz.interfaces.binarypackagerelease import *
from lp.soyuz.interfaces.binarypackagename import *
from lp.soyuz.interfaces.binarypackagebuild import *
from lp.soyuz.interfaces.buildrecords import *
from lp.soyuz.interfaces.component import *
from lp.soyuz.interfaces.distributionsourcepackagecache import *
from lp.soyuz.interfaces.distributionsourcepackagerelease import *
from lp.soyuz.interfaces.distroarchseries import *
from lp.soyuz.interfaces.distroarchseriesbinarypackage import *
from lp.soyuz.interfaces.distroarchseriesbinarypackagerelease import *
from lp.soyuz.interfaces.distroseriesbinarypackage import *
from lp.soyuz.interfaces.distroseriespackagecache import *
from lp.soyuz.interfaces.distroseriessourcepackagerelease import *
from lp.soyuz.interfaces.files import *
from lp.soyuz.interfaces.processor import *
from lp.soyuz.interfaces.publishedpackage import *
from lp.soyuz.interfaces.publishing import *
from lp.soyuz.interfaces.queue import *
from lp.soyuz.interfaces.section import *
from lp.soyuz.interfaces.sourcepackagerelease import *
from lp.soyuz.interfaces.packagediff import *
from lp.soyuz.interfaces.packageset import *

from lp.services.worlddata.interfaces.country import *
from lp.services.worlddata.interfaces.language import *
from lp.services.worlddata.interfaces.spokenin import *

from lp.blueprints.interfaces.specification import *
from lp.blueprints.interfaces.specificationbranch import *


from canonical.launchpad.interfaces._schema_circular_imports import *

