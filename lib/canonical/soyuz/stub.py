"""Stub backend for Soyuz.

(c) Canonical Software Ltd. 2004, all rights reserved.
"""

__metaclass__ = type

from zope.interface import implements
from canonical.launchpad.interfaces import IPackages, IBinaryPackage, IBinaryPackageSet, IProjectSet, IProject, IProduct, ISync

class Packages:
    """Stub packages collection"""

    implements(IPackages)
    
    def __getitem__(self, name):
        if name == 'binary':
            return BinaryPackages()
        else:
            raise KeyError, name

    def __iter__(self):
        yield BinaryPackages()

class BinaryPackages:
    """Stub binary packages collection"""

    implements(IBinaryPackageSet)

    def __init__(self):
        self.mozilla = BinaryPackage('mozilla')
        self.evolution = BinaryPackage('evolution')

    def __getitem__(self, name):
        """See IBinaryPackages."""
        if name == 'mozilla':
            return self.mozilla
        elif name == 'evolution':
            return self.evolution
        else:
            raise KeyError, name

    def __iter__(self):
        for package in self.mozilla, self.evolution:
            yield package


class BinaryPackage:
    """Stub package"""

    implements(IBinaryPackage)

    def __init__(self, name):
        self.name = name

import canonical.rosetta.stub


class Projects(object):
    """Stub projects collection"""

    implements(IProjectSet)
    _projects=[]

    def __init__(self):
        """"""

    def projects(self):
        return self.__iter__()

    def __iter__(self):
        """Iterate over all the projects."""
        for project in self._projects:
            yield project

    def __getitem__(self, name):
        """Get a project by its name."""
        for project in self._projects:
            if project.name == name:
                return project
        raise KeyError, name

    def new(self, name, title, description, url):
        """Creates a new project with the given name.

        Returns that project.
        """
        self._projects.append(Project(name, title, description, url))
        return self._projects[-1]

    
class Project(object):
    """Stub project"""

    implements(IProject)

    def __init__(self, name, title, url, description):
        self.name = name
        self.title = title
        self.url = url
        self.description = description
        self._products = []

    def potFiles(self):
        """Returns an iterator over this project's pot files."""
        for product in self._products:
            for potfile in product.potFiles():
                yield potfile

    def products(self):
        """Returns an iterator over this projects products."""
        return iter(self._products)

    def potFile(self, name):
        """Returns the pot file with the given name."""
        for potfile in self.potFiles():
            if potfile.name == name:
                return potfile
        raise KeyError, name

    def newProduct(self, name, title, description, url):
        """well, duh"""
        self._products.append(Product(name, title, description, url))
        return self._products[-1]

    def getProduct(self, name):
        """find a product"""
        for product in self.products():
            if product.name == name:
                return product
        raise KeyError, name

class Product(object):
    """Stub product."""

    implements(IProduct)

    def __init__(self, name, title, description, url):
        self.name = name
        self.title = title
        self.description = description
        self.url = url
        self._potfiles = []
        self._syncs=[]

    def potFiles(self):
        for potfile in self._potfiles:
            yield potfile

    def getSync(self, name):
        for sync in self.syncs():
            if sync.name == name:
                return sync
        raise KeyError, name

    def syncs(self):
        return iter(self._syncs)

    def newSync(self, **kwargs):
        """phwoar"""
        self._syncs.append(Sync(**kwargs))
        return self._syncs[-1]

class Sync(object):
    """oi, vey!"""
    implements(ISync)
    def __init__(self, **kwargs):
        for attribute,value in kwargs.items():
            setattr(self, attribute, value)
    def update(self, **kwargs):
        """update a Sync, possibly reparenting"""
        for attribute,value in kwargs.items():
            setattr(self, attribute, value)


# arch-tag: b220d005-dd14-4af1-bbfa-b17a24e3bf70
