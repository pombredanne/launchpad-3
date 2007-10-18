# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Content classes for the 'home pages' of the subsystems of Launchpad."""

__all__ = [
    'BazaarApplication',
    'FeedsApplication',
    'MailingListApplication',
    'MaloneApplication',
    'RegistryApplication',
    'RosettaApplication',
    'ShipItApplication',
    ]

__metaclass__ = type

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import (
    BugTaskSearchParams, IBazaarApplication, IBugExternalRefSet,
    IBugSet, IBugTaskSet, IBugTrackerSet, IBugWatchSet, IDistroSeriesSet,
    IFeedsApplication, IHWDBApplication, ILanguageSet, ILaunchBag,
    ILaunchpadStatisticSet, IMailingListApplication, IMaloneApplication,
    IOpenIdApplication, IProductSet, IRegistryApplication,
    IRosettaApplication, IShipItApplication, ITranslationGroupSet)


class RegistryApplication:
    implements(IRegistryApplication)


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
        """See IMaloneApplication."""
        return getUtility(IBugTaskSet).search(search_params)

    @property
    def bug_count(self):
        user = getUtility(ILaunchBag).user
        return getUtility(IBugSet).searchAsUser(user=user).count()

    @property
    def bugwatch_count(self):
        return getUtility(IBugWatchSet).search().count()

    @property
    def bugextref_count(self):
        return getUtility(IBugExternalRefSet).search().count()

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


class BazaarApplication:
    implements(IBazaarApplication)

    def __init__(self):
        self.title = 'The Open Source Bazaar'


class OpenIdApplication:
    implements(IOpenIdApplication)

    title = 'Launchpad Login Service'


class RosettaApplication:
    implements(IRosettaApplication)

    def __init__(self):
        self.title = 'Rosetta: Translations in the Launchpad'
        self.name = 'Rosetta'

    @property
    def languages(self):
        """See IRosettaApplication."""
        return getUtility(ILanguageSet)

    @property
    def language_count(self):
        """See IRosettaApplication."""
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.value('language_count')

    @property
    def statsdate(self):
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.dateupdated('potemplate_count')

    @property
    def translation_groups(self):
        """See IRosettaApplication."""
        return getUtility(ITranslationGroupSet)

    def translatable_products(self):
        """See IRosettaApplication."""
        products = getUtility(IProductSet)
        return products.getTranslatables()

    def featured_products(self):
        """See IRosettaApplication."""
        products = getUtility(IProductSet)
        return products.featuredTranslatables()

    def translatable_distroseriess(self):
        """See IRosettaApplication."""
        distroseriess = getUtility(IDistroSeriesSet)
        return distroseriess.translatables()

    def potemplate_count(self):
        """See IRosettaApplication."""
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.value('potemplate_count')

    def pofile_count(self):
        """See IRosettaApplication."""
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.value('pofile_count')

    def pomsgid_count(self):
        """See IRosettaApplication."""
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.value('pomsgid_count')

    def translator_count(self):
        """See IRosettaApplication."""
        stats = getUtility(ILaunchpadStatisticSet)
        return stats.value('translator_count')


class HWDBApplication:
    implements(IHWDBApplication)
