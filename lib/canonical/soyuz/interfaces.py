
from zope.interface import Interface, Attribute

# Web UI interfaces

class IPackages(Interface):
    """Root object for web app."""
    binary = Attribute("Binary packages")
    source = Attribute("Source packages")

    def __getitem__(name):
        """Retrieve a package set by name."""

class IDistributions(Interface):
    """Root object for collection of Distributions"""
    def __getitem__(name):
        """retrieve distribution by name"""
    def distributions():
        """retrieve all projects"""

    def __iter__():
        """retrieve an iterator"""

    def new(name, title, description, url):
        """Creates a new distribution with the given name.

        Returns that project.
        """
class IDistribution(Interface):
    """A Distribution Object"""
    id = Attribute("The distro's unique number.")
    name = Attribute("The distro's name.")
    title = Attribute("The distro's title.")
    description = Attribute("The distro's description.")
    domainname = Attribute("The distro's domain name.")
    owner = Attribute("The distro's owner.")

    def getReleaseContainer(name):
        """Returns an associated IReleaseContainer"""


class IReleaseContainer(Interface):
    """Root object for collection of Releases"""
    distribution = Attribute("distribution")

    def __getitem__(name):
        """retrieve distribution by name"""

    def releases():
        """retrieve all projects"""

    def __iter__():
        """retrieve an iterator"""

    def new(name, title, description, url):
        """Creates a new distribution with the given name.

        Returns that project.
        """

class IRelease(Interface):
    """A Release Object"""
    distribution = Attribute("The release's reference.")
    name= Attribute("The release's name.")
    title = Attribute("The release's title.")
    description = Attribute("The release's description.")
    version = Attribute("The release's version")
    componentes = Attribute("The release componentes.")
    sections = Attribute("The release section.")
    releasestate = Attribute("The release's state.")
    datereleased = Attribute("The datereleased.")

    def getPackageContainer(name):
        """ Returns the associated IPackageSet """

################################################################
   
class IProjects(Interface):
    """Root object for collection of projects"""
    def __getitem__(name):
        """retrieve project by name"""
    def projects():
        """retrieve all projects"""

    def __iter__():
        """retrieve an iterator"""

    def new(name, title, description, url):
        """Creates a new project with the given name.

        Returns that project.
        """


class IProject(Interface):
    """A Project"""

    name = Attribute("The project's name. (unique within IProjects)")

    title = Attribute("The project's title.")

    url = Attribute("The URL of the project's website.")

    description = Attribute("The project's description.")

    def potFiles():
        """Returns an iterator over this project's pot files."""

    def products():
        """Returns an iterator over this projects products."""

    def potFile(name):
        """Returns the pot file with the given name."""

    def newProduct(name, title, description, url):
        """make a new product"""
    def getProduct(name):
        """blah"""
        
class IProduct(Interface):
    """A Product.  For example 'firefox' in the 'mozilla' project."""

    name = Attribute("The product's name, unique within a project.")

    title = Attribute("The product's title.")

    description = Attribute("The product's description")

    project = Attribute("The product's project.")

    def potFiles():
        """Returns an iterator over this product's pot files."""

    def newPotFile(branch):
        """Creates a new POT file.

        Returns the newly created POT file.
        """

    def branches():
        """Iterate over this product's branches."""

    def syncs():
        """iterate over this products syncs"""
    def newSync(**kwargs):
        """create a new sync job"""
    def getSync(name):
        """get a sync"""

class ISync(Interface):
    """A sync job"""

    name = Attribute("the syncs name, not title, no matter how much you think it should be")
    title = Attribute("duh")
    description = Attribute("duh")
    cvsroot = Attribute("duh")
    module = Attribute("duh")
    cvstarfile = Attribute("duh")
    branchfrom = Attribute("duh")
    svnrepository = Attribute("duh")
    category = Attribute("duh")
    branchto = Attribute("duh")
    archversion = Attribute("duh")
    archsourcegpgkeyid = Attribute("duh")
    archsourcename = Attribute("duh")
    archsourceurl = Attribute("duh")

    def update(**kwargs):
        """update a Sync, possibly reparenting"""

class IPackageSet(Interface):
    """A set of packages"""
    def __getitem__(name):
        """Retrieve a package by name."""
    def __iter__():
        """Iterate over names"""


class ISourcePackageSet(IPackageSet):
    """A set of source packages"""
    

class IBinaryPackageSet(IPackageSet):
    """A set of binary packages"""
    

# Interfaces from the DB

class IBinaryPackage(Interface):
    """A binary package, e.g apache-utils"""
    # See the BinaryPackage table

    name = Attribute("A string")
    title = Attribute("Package Title")
    description = Attribute("Package Description")
    ##releases = Attribute("List of IBinaryPackageRelease objects")


class IBinaryPackageRelease(Interface):
    """A binary package release, e.g apache-utils 2.0.48-4_i386"""
    # See the BinaryPackageRelease table

    name = Attribute("A string")
    version = Attribute("A version string")
    sourceRelease = Attribute("An ISourcePackageRelease")


class ISourcePackage(Interface):
    """A source package, e.g apache-utils"""
    # See the SourcePackage table

    name = Attribute("A string")
    title = Attribute("Package Title")
    description = Attribute("Package Description")
    ##releases = Attribute("List of ISourcePackageRelease objects")


class ISourcePackageRelease(Interface):
    """A source package release, e.g. apache-utils 2.0.48-3"""
    # See the SourcePackageRelease table

    version = Attribute("A version string")
    creator = Attribute("Person that created this release")

    def branches():
        """Return the list of branches in a source package release"""


class IPerson(Interface):
    """A person"""

    givenName = Attribute("Given name")
    familyName = Attribute("Family name")
    presentationName = Attribute("Presentation name")


class IManifestEntry(Interface):
    """"""
    branch = Attribute("A branch")


class IBranch(Interface):
    """A branch of some source code"""

    changesets = Attribute("List of changesets in a branch")


class IChangeset(Interface):
    """A changeset"""

    message = Attribute("The log message for this changeset")

# arch-tag: 3f98fde9-9a5b-447b-93e7-e4a9c770ca63
