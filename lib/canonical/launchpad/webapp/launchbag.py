'''
LaunchBag

The collection of stuff we have traversed to.
'''

from zope.interface import Interface, implements
from zope.app.zapi import getUtility
import zope.security.management
from canonical.launchpad.interfaces import \
        IOpenLaunchBag, ILaunchBag, \
        ILaunchpadApplication, IPerson, IProject, IProduct, IDistribution, \
        ISourcePackage
import zope.thread

class LaunchBag(object):

    implements(IOpenLaunchBag)

    # Map Interface to attribute name.
    _registry = {
        ILaunchpadApplication: 'site',
        IPerson: 'person',
        IProject: 'project',
        IProduct: 'product',
        IDistribution: 'distribution',
        ISourcePackage: 'sourcepackage',
        }

    _store = zope.thread.local()

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
            return IPerson(principals[0])
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

    def sourcepackage(self):
        return self._store.sourcepackage
    sourcepackage = property(sourcepackage)

class LaunchBagView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.bag = getUtility(ILaunchBag)

