# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Content classes for the 'home pages' of the subsystems of Launchpad."""

__all__ = [
    'AuthServerApplication',
    'BazaarApplication',
    'CodeImportScheduler',
    'FeedsApplication',
    'MailingListApplication',
    'MaloneApplication',
    'PrivateMaloneApplication',
    'RosettaApplication',
    'ShipItApplication',
    ]

__metaclass__ = type

import codecs
import os

from zope.component import getUtility
from zope.interface import implements

from canonical.config import config
from canonical.launchpad.interfaces.bug import (
    CreateBugParams, IBugSet, InvalidBugTargetType)
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage)
from canonical.launchpad.interfaces import (
    BugTaskSearchParams, IAuthServerApplication, IBazaarApplication,
    IBugTaskSet, IBugTrackerSet, IBugWatchSet,
    ICodeImportSchedulerApplication, IDistroSeriesSet, IFeedsApplication,
    IHWDBApplication, ILanguageSet, ILaunchBag, ILaunchpadStatisticSet,
    IMailingListApplication, IMaloneApplication, IOpenIDApplication,
    IPrivateMaloneApplication, IProductSet, IRosettaApplication,
    IShipItApplication, ITranslationGroupSet, ITranslationsOverview,
    IWebServiceApplication)
from lp.code.interfaces.codehosting import (
    IBranchFileSystemApplication, IBranchPullerApplication)
from canonical.launchpad.interfaces.hwdb import (
    IHWDeviceSet, IHWDriverSet, IHWVendorIDSet)
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from lazr.restful import ServiceRootResource


class AuthServerApplication:
    """AuthServer End-Point."""
    implements(IAuthServerApplication)

    title = "Auth Server"


class BranchFileSystemApplication:
    """BranchFileSystem End-Point."""
    implements(IBranchFileSystemApplication)

    title = "Branch File System"


class BranchPullerApplication:
    """BranchPuller End-Point."""
    implements(IBranchPullerApplication)

    title = "Puller API"


class CodeImportSchedulerApplication:
    """CodeImportScheduler End-Point."""
    implements(ICodeImportSchedulerApplication)

    title = "Code Import Scheduler"


class PrivateMaloneApplication:
    """ExternalBugTracker authentication token end-point."""
    implements(IPrivateMaloneApplication)

    title = "Launchpad Bugs."


class ShipItApplication:
    implements(IShipItApplication)


class MailingListApplication:
    implements(IMailingListApplication)


class FeedsApplication:
    implements(IFeedsApplication)


class MaloneApplication:
    implements(IMaloneApplication)

    def __init__(self):
        self.title = 'Malone: the Launchpad bug tracker'

    def searchTasks(self, search_params):
        """See `IMaloneApplication`."""
        return getUtility(IBugTaskSet).search(search_params)

    def createBug(self, owner, title, description, target,
                  security_related=False, private=False, tags=None):
        """See `IMaloneApplication`."""
        params = CreateBugParams(
            title=title, comment=description, owner=owner,
            security_related=security_related, private=private, tags=tags)
        if IProduct.providedBy(target):
            params.setBugTarget(product=target)
        elif IDistribution.providedBy(target):
            params.setBugTarget(distribution=target)
        elif IDistributionSourcePackage.providedBy(target):
            params.setBugTarget(distribution=target.distribution,
                                sourcepackagename=target.sourcepackagename)
        else:
            raise InvalidBugTargetType(
                "A bug target must be a Project, a Distribution or a "
                "DistributionSourcePackage. Got %r." % target)
        return getUtility(IBugSet).createBug(params)

    @property
    def bug_count(self):
        user = getUtility(ILaunchBag).user
        return getUtility(IBugSet).searchAsUser(user=user).count()

    @property
    def bugwatch_count(self):
        return getUtility(IBugWatchSet).search().count()

    @property
    def bugtask_count(self):
        user = getUtility(ILaunchBag).user
        search_params = BugTaskSearchParams(user=user)
        return getUtility(IBugTaskSet).search(search_params).count()

    @property
    def bugtracker_count(self):
        return getUtility(IBugTrackerSet).search().count()

    @property
    def projects_with_bugs_count(self):
        return getUtility(ILaunchpadStatisticSet).value('projects_with_bugs')

    @property
    def shared_bug_count(self):
        return getUtility(ILaunchpadStatisticSet).value('shared_bug_count')

    @property
    def top_bugtrackers(self):
        return getUtility(IBugTrackerSet).getMostActiveBugTrackers(limit=5)

    @property
    def latest_bugs(self):
        user = getUtility(ILaunchBag).user
        return getUtility(IBugSet).searchAsUser(
            user=user, orderBy='-datecreated', limit=5)

    def default_bug_list(self, user=None):
        return getUtility(IBugSet).searchAsUser(user)


class BazaarApplication:
    implements(IBazaarApplication)

    def __init__(self):
        self.title = 'The Open Source Bazaar'


class OpenIDApplication:
    implements(IOpenIDApplication)

    title = 'Launchpad Login Service'


class RosettaApplication:
    implements(IRosettaApplication)

    def __init__(self):
        self.title = 'Rosetta: Translations in the Launchpad'
        self.name = 'Rosetta'

    @property
    def languages(self):
        """See `IRosettaApplication`."""
        return getUtility(ILanguageSet)

    @property
    def language_count(self):
        """See `IRosettaApplication`."""
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.value('language_count')

    @property
    def statsdate(self):
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.dateupdated('potemplate_count')

    @property
    def translation_groups(self):
        """See `IRosettaApplication`."""
        return getUtility(ITranslationGroupSet)

    def translatable_products(self):
        """See `IRosettaApplication`."""
        products = getUtility(IProductSet)
        return products.getTranslatables()

    def featured_products(self):
        """See `IRosettaApplication`."""
        projects = getUtility(ITranslationsOverview)
        for project in projects.getMostTranslatedPillars():
            yield { 'pillar' : project['pillar'],
                    'font_size' : project['weight'] * 10 }

    def translatable_distroseriess(self):
        """See `IRosettaApplication`."""
        distroseriess = getUtility(IDistroSeriesSet)
        return distroseriess.translatables()

    def potemplate_count(self):
        """See `IRosettaApplication`."""
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.value('potemplate_count')

    def pofile_count(self):
        """See `IRosettaApplication`."""
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.value('pofile_count')

    def pomsgid_count(self):
        """See `IRosettaApplication`."""
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.value('pomsgid_count')

    def translator_count(self):
        """See `IRosettaApplication`."""
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.value('translator_count')


class HWDBApplication:
    """See `IHWDBApplication`."""
    implements(IHWDBApplication)

    link_name = 'hwdb'
    entry_type = IHWDBApplication

    def devices(self, bus, vendor_id, product_id=None):
        """See `IHWDBApplication`."""
        return getUtility(IHWDeviceSet).search(bus, vendor_id, product_id)

    def drivers(self, package_name=None, name=None):
        """See `IHWDBApplication`."""
        return getUtility(IHWDriverSet).search(package_name, name)

    def vendorIDs(self, bus):
        """See `IHWDBApplication`."""
        return getUtility(IHWVendorIDSet).idsForBus(bus)

    @property
    def package_names(self):
        """See `IHWDBApplication`."""
        return getUtility(IHWDriverSet).package_names


class WebServiceApplication(ServiceRootResource):
    """See `IWebServiceApplication`.

    This implementation adds a 'cached_wadl' attribute.  If set, it will be
    served by `toWADL` rather than calculating the toWADL result.

    On import, the class tries to load a file to populate this attribute.  By
    doing it on import, this makes it easy to clear, as is needed by
    utilities/create-lp-wadl.py.

    If the attribute is not set, toWADL will set the attribute on the class
    once it is calculated.
    """
    implements(IWebServiceApplication, ICanonicalUrlData)

    inside = None
    path = ''
    rootsite = None

    _wadl_filename = os.path.join(
        os.path.dirname(os.path.normpath(__file__)),
        'apidoc', 'wadl-%s.xml' % config.instance_name)

    cached_wadl = None

    # Attempt to load the WADL.
    _wadl_fd = None
    try:
        _wadl_fd = codecs.open(_wadl_filename, encoding='UTF-8')
        try:
            cached_wadl = _wadl_fd.read()
        finally:
            _wadl_fd.close()
    except IOError:
        pass
    del _wadl_fd

    def toWADL(self):
        """See `IWebServiceApplication`."""
        if self.cached_wadl is not None:
            return self.cached_wadl
        wadl = super(WebServiceApplication, self).toWADL()
        self.__class__.cached_wadl = wadl
        return wadl
