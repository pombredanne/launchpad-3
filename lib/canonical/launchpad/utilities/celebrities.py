# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Classes that implement ICelebrity interfaces."""

__metaclass__ = type
__all__ = ['LaunchpadCelebrities']

from zope.interface import implements
from zope.component import getUtility
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, IPersonSet, IDistributionSet, IBugTrackerSet,
    IProductSet, NotFoundError, IDistributionMirrorSet)

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

    def __get__(self, instance, cls=None):
        if instance is None:
            return self

        utility = getUtility(self.interface)
        if self.id is None:
            try:
                celebrity = utility.getByName(self.name)
                if celebrity is None:
                    raise MissingCelebrityError(self.name)
            except NotFoundError:
                raise MissingCelebrityError(self.name)
            self.id = celebrity.id
        else:
            try:
                celebrity = utility.get(self.id)
                if celebrity is None or celebrity.name != self.name:
                    raise MutatedCelebrityError(self.name)
            except NotFoundError:
                raise MutatedCelebrityError(self.name)
        return celebrity


class LaunchpadCelebrities:
    """See `ILaunchpadCelebrities`."""
    implements(ILaunchpadCelebrities)

    admin = CelebrityDescriptor(IPersonSet, 'admins')
    ubuntu = CelebrityDescriptor(IDistributionSet, 'ubuntu')
    debian = CelebrityDescriptor(IDistributionSet, 'debian')
    rosetta_experts = CelebrityDescriptor(IPersonSet, 'rosetta-admins')
    bazaar_expert = CelebrityDescriptor(IPersonSet, 'vcs-imports')
    vcs_imports = CelebrityDescriptor(IPersonSet, 'vcs-imports')
    debbugs = CelebrityDescriptor(IBugTrackerSet, 'debbugs')
    sourceforge_tracker = CelebrityDescriptor(IBugTrackerSet, 'sf')
    shipit_admin = CelebrityDescriptor(IPersonSet, 'shipit-admins')
    buildd_admin = CelebrityDescriptor(IPersonSet, 'launchpad-buildd-admins')
    launchpad_developers = CelebrityDescriptor(IPersonSet, 'launchpad')
    ubuntu_bugzilla = CelebrityDescriptor(IBugTrackerSet, 'ubuntu-bugzilla')
    registry = CelebrityDescriptor(IPersonSet, 'registry')
    bug_watch_updater = CelebrityDescriptor(IPersonSet, 'bug-watch-updater')
    bug_importer = CelebrityDescriptor(IPersonSet, 'bug-importer')
    launchpad = CelebrityDescriptor(IProductSet, 'launchpad')
    launchpad_beta_testers = CelebrityDescriptor(
        IPersonSet, 'launchpad-beta-testers')
    janitor = CelebrityDescriptor(IPersonSet, 'janitor')
    mailing_list_experts = CelebrityDescriptor(
        IPersonSet, 'mailing-list-experts')

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

