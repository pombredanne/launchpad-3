# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Classes that implement ICelebrity interfaces."""

__metaclass__ = type
__all__ = ['LaunchpadCelebrities']

from zope.interface import implements
from zope.component import getUtility
from canonical.launchpad.interfaces import (
    ILanguageSet, ILaunchpadCelebrities, IPersonSet, IDistributionSet,
    IBugTrackerSet, IProductSet, NotFoundError, IDistributionMirrorSet)

class MutatedCelebrityError(Exception):
    """A celebrity has had its id or name changed in the database.

    This would indicate a major prodution screwup.
    """


class MissingCelebrityError(Exception):
    """A celebrity cannot be found in the database.

    Usually this means it has not yet been created.
    """


class CelebrityDescriptor:
    """An attribute of LaunchpadCelebrities

    This descriptor removes unnecessary boilerplate from the
    LaunchpadCelebrities attribute, as well as optimizing database
    access to ensure that using a celebrity causes at most one
    database query per request.

    TODO: By implementing a suitably clever wrapper, we should be able
    to reduce the queries further, as we will only ever need to really
    query the database if code attempts to access attributes of the
    celebrity besides the non-volatile id and name attributes. However,
    this is non trivial as we need to ensure that security and interface
    declarations remain unchanged. Perhaps we need a way of instantiating
    SQLObject instances in a 'lazy' mode? Or perhaps we should not worry
    about volatile attribute changes and pass a selectResults value through
    to the SQLObject.get method, which should allow us to instantiate a
    real instance without hitting the database. -- StuartBishop 20060123
    """
    interface = None
    name = None
    id = None

    def __init__(self, interface, name):
        """Interface is used to lookup a utility which must have both
        a get method to lookup by id, and a getByName method to lookup by
        name.
        """
        self.interface = interface
        self.name = name

    def _getCelebrityByName(self, utility):
        """Find the celebrity by name."""
        return utility.getByName(self.name)

    def _isRightCelebrity(self, celebrity):
        """Is this the celebrity we were looking for?"""
        return celebrity.name == self.name

    def __get__(self, instance, cls=None):
        if instance is None:
            return self

        utility = getUtility(self.interface)
        if self.id is None:
            try:
                celebrity = self._getCelebrityByName(utility)
                if celebrity is None:
                    raise MissingCelebrityError(self.name)
            except NotFoundError:
                raise MissingCelebrityError(self.name)
            self.id = celebrity.id
        else:
            try:
                celebrity = utility.get(self.id)
                if celebrity is None or not self._isRightCelebrity(celebrity):
                    raise MutatedCelebrityError(self.name)
            except NotFoundError:
                raise MutatedCelebrityError(self.name)
        return celebrity


class LanguageCelebrityDescriptor(CelebrityDescriptor):
    """A `CelebrityDescriptor` for celebrities that are languages.

    Unlike most other celebrities, languages are retrieved by code.
    """
    def _getCelebrityByName(self, utility):
        """See `CelebrityDescriptor`."""
        return utility.getLanguageByCode(self.name)

    def _isRightCelebrity(self, celebrity):
        """See `CelebrityDescriptor`."""
        return celebrity.code == self.name


class LaunchpadCelebrities:
    """See `ILaunchpadCelebrities`."""
    implements(ILaunchpadCelebrities)

    admin = CelebrityDescriptor(IPersonSet, 'admins')
    bazaar_experts = CelebrityDescriptor(IPersonSet, 'bazaar-experts')
    bug_importer = CelebrityDescriptor(IPersonSet, 'bug-importer')
    bug_watch_updater = CelebrityDescriptor(IPersonSet, 'bug-watch-updater')
    buildd_admin = CelebrityDescriptor(IPersonSet, 'launchpad-buildd-admins')
    commercial_admin = CelebrityDescriptor(IPersonSet, 'commercial-admins')
    debbugs = CelebrityDescriptor(IBugTrackerSet, 'debbugs')
    debian = CelebrityDescriptor(IDistributionSet, 'debian')
    english = LanguageCelebrityDescriptor(ILanguageSet, 'en')
    gnome_bugzilla = CelebrityDescriptor(IBugTrackerSet, 'gnome-bugs')
    hwdb_team = CelebrityDescriptor(IPersonSet, 'hwdb-team')
    janitor = CelebrityDescriptor(IPersonSet, 'janitor')
    katie = CelebrityDescriptor(IPersonSet, 'katie')
    launchpad = CelebrityDescriptor(IProductSet, 'launchpad')
    launchpad_beta_testers = CelebrityDescriptor(
        IPersonSet, 'launchpad-beta-testers')
    launchpad_developers = CelebrityDescriptor(IPersonSet, 'launchpad')
    lp_translations = CelebrityDescriptor(IProductSet, 'rosetta')
    mailing_list_experts = CelebrityDescriptor(
        IPersonSet, 'mailing-list-experts')
    obsolete_junk = CelebrityDescriptor(IProductSet, 'obsolete-junk')
    ppa_key_guard = CelebrityDescriptor(IPersonSet, 'ppa-key-guard')
    registry_experts = CelebrityDescriptor(IPersonSet, 'registry')
    rosetta_experts = CelebrityDescriptor(IPersonSet, 'rosetta-admins')
    savannah_tracker = CelebrityDescriptor(IBugTrackerSet, 'savannah')
    shipit_admin = CelebrityDescriptor(IPersonSet, 'shipit-admins')
    sourceforge_tracker = CelebrityDescriptor(IBugTrackerSet, 'sf')
    ubuntu = CelebrityDescriptor(IDistributionSet, 'ubuntu')
    ubuntu_branches = CelebrityDescriptor(IPersonSet, 'ubuntu-branches')
    ubuntu_bugzilla = CelebrityDescriptor(IBugTrackerSet, 'ubuntu-bugzilla')
    vcs_imports = CelebrityDescriptor(IPersonSet, 'vcs-imports')

    @property
    def ubuntu_archive_mirror(self):
        """See `ILaunchpadCelebrities`."""
        mirror = getUtility(IDistributionMirrorSet).getByHttpUrl(
            'http://archive.ubuntu.com/ubuntu/')
        if mirror is None:
            raise MissingCelebrityError('http://archive.ubuntu.com/ubuntu/')
        assert mirror.isOfficial(), "Main mirror must be an official one."
        return mirror

    @property
    def ubuntu_cdimage_mirror(self):
        """See `ILaunchpadCelebrities`."""
        mirror = getUtility(IDistributionMirrorSet).getByHttpUrl(
            'http://releases.ubuntu.com/')
        if mirror is None:
            raise MissingCelebrityError('http://releases.ubuntu.com/')
        assert mirror.isOfficial(), "Main mirror must be an official one."
        return mirror
