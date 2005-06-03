# Copyright 2004 Canonical Ltd.  All rights reserved.
"""
LaunchBag

The collection of stuff we have traversed.
"""
__metaclass__ = type

import pytz

from zope.interface import Interface, implements
from zope.component import getUtility
import zope.security.management
import zope.thread
from zope.app.session.interfaces import ISession

from canonical.launchpad.interfaces import \
        IOpenLaunchBag, ILaunchBag, \
        ILaunchpadApplication, IPerson, IProject, IProduct, IDistribution, \
        IDistroRelease, ISourcePackage, IBug, ISourcePackageReleasePublishing
from canonical.launchpad.webapp.interfaces import ILoggedInEvent

_utc_tz = pytz.timezone('UTC')

class LaunchBag(object):

    implements(IOpenLaunchBag)

    # Map Interface to attribute name.
    _registry = {
        ILaunchpadApplication: 'site',
        IPerson: 'person',
        IProject: 'project',
        IProduct: 'product',
        IDistribution: 'distribution',
        IDistroRelease: 'distrorelease', 
        ISourcePackage: 'sourcepackage',
        ISourcePackageReleasePublishing: 'sourcepackagereleasepublishing',
        IBug: 'bug',
        }

    _store = zope.thread.local()

    def setLogin(self, login):
        '''See IOpenLaunchBag.'''
        self._store.login = login

    def login(self):
        return getattr(self._store, 'login', None)
    login = property(login)

    def user(self):
        interaction = zope.security.management.queryInteraction()
        principals = [
            participation.principal
            for participation in list(interaction.participations)
            if participation.principal is not None
            ]
        if not principals:
            return None
        elif len(principals) > 1:
            raise ValueError, 'Too many principals'
        else:
            try:
                person = IPerson(principals[0])
            except TypeError, err:
                person = None
            return person

    user = property(user)

    def add(self, obj):
        store = self._store
        for interface, attribute in self._registry.items():
            if interface.providedBy(obj):
                setattr(store, attribute, obj)

    def clear(self):
        store = self._store
        for attribute in self._registry.values():
            setattr(store, attribute, None)
        store.login = None

    def site(self):
        return self._store.site
    site = property(site)

    def person(self):
        return self._store.person
    person = property(person)

    def project(self):
        store = self._store
        if store.project is not None:
            return store.project
        elif store.product is not None:
            return store.product.project
        else:
            return None
    project = property(project)

    def product(self):
        return self._store.product
    product = property(product)

    def distribution(self):
        return self._store.distribution
    distribution = property(distribution)

    def distrorelease(self):
        return self._store.distrorelease
    distrorelease = property(distrorelease)

    def sourcepackage(self):
        return self._store.sourcepackage
    sourcepackage = property(sourcepackage)

    def sourcepackagereleasepublishing(self):
        return self._store.sourcepackagereleasepublishing
    sourcepackagereleasepublishing = property(sourcepackagereleasepublishing)

    def bug(self):
        return self._store.bug
    bug = property(bug)

    def timezone(self):
        user = self.user
        if user and user.timezone_name:
            try:
                return pytz.timezone(user.timezone_name)
            except KeyError:
                pass # unknown timezone name
        # fall back to UTC
        return _utc_tz
    timezone = property(timezone)

class LaunchBagView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.bag = getUtility(ILaunchBag)


def set_login_in_launchbag_when_principal_identified(event):
    """Subscriber for IPrincipalIdentifiedEvent that sets 'login' in launchbag.
    """
    launchbag = getUtility(IOpenLaunchBag)
    loggedinevent = ILoggedInEvent(event, None)
    if loggedinevent is None:
        # We must be using session auth.
        session = ISession(event.request)
        authdata = session['launchpad.authenticateduser']
        assert authdata['personid'] == event.principal.id
        launchbag.setLogin(authdata['login'])
    else:
        launchbag.setLogin(loggedinevent.login)

def reset_login_in_launchbag_on_logout(event):
    """Subscriber for ILoggedOutEvent that sets 'login' in launchbag to None.
    """
    launchbag = getUtility(IOpenLaunchBag)
    launchbag.setLogin(None)
