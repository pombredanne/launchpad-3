
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

class IDistroReleasesApp(Interface):
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

class IDistroReleaseSourcesApp(Interface):
    """A Release Sources Proxy """
    release = Attribute("Release")
    
    def __getitem__(name):
        """Retrieve a package by name."""
    def __iter__():
        """Iterate over names"""

    
class IDistroReleaseSourceApp(Interface):
    """A SourcePackage Proxy """
    sourcepackage = Attribute("SourcePackage")
    proposed = Attribute("Proposed source package release")
    lastversions = Attribute("Last Release Versions")
    currentversions = Attribute("Current Release Versions")
    
    def __getitem__(name):
        """Retrieve a package release by version."""

class IDistroReleaseSourceReleaseBuildApp(Interface):
        sourcepackagerelease = Attribute("SourcePackageRelease")
        arch = Attribute("Builded arch")

class IDistroReleaseSourceReleaseApp(Interface):
    """A SourcePackageRelease Proxy """
    sourcepackagerelease = Attribute("SourcePackageRelease")
    archs = Attribute("Builded archs")

    def __getitem__(name):
        """Retrieve a package release build by arch."""


class IDistroReleaseApp(Interface):
    """A Release Proxy """
    release = Attribute("Release")
    name = Attribute("Release name")
    title = Attribute("Release title")
    description = Attribute("Release description")
    version = Attribute("Release version")

    def getPackageContainer(name):
        """ Returns the associated IPackageSet """


class IDistroBinariesApp(Interface):
    """A Binaries Source Tag """
    distribution = Attribute("Distribution")

    def __getitem__(name):
        """retrieve binarypackges by distribution"""

    def __iter__():
        """retrieve an iterator"""

class IDistroReleaseBinariesApp(Interface):
    """A Release Binary Tag """
    release = Attribute("Release")

    def __getitem__(name):
        """retrieve binarypackges by release"""

    def __iter__():
        """retrieve an iterator"""

class IDistroReleaseBinaryReleaseBuildApp(Interface):
    binarypackagerelease = Attribute("Release")
    version = Attribute("Version")
    arch = Attribute("Arch")



class IDistroReleaseBinaryReleaseApp(Interface):
    """A Binary Release Proxy """
    binarypackagerelease = Attribute("BinaryPackageRelease")
    version = Attribute("BinaryPackageRelease Version ?!?!")
    archs = Attribute("Builded archs")

    def __getitem__(name):
        """retrieve binarypackagesbuild by version"""


class IDistroReleaseBinaryApp(Interface):    
    """A Binary Package Proxy """
    binarypackage = Attribute("BinaryPackage")
    lastversions = Attribute("Last Release Versions")
    currentversions = Attribute("Current Release Versions")

    def __getitem__(name):
        """Retrieve a package release by version."""



class IDistroSourcesApp(Interface):
    """A Distribution Source Tag """
    distribution = Attribute("Distribution")

    def __getitem__(name):
        """retrieve sourcepackges by release"""

    def __iter__():
        """retrieve an iterator"""
     
class IDistroTeamApp(Interface):
    """A Distribution Team Tag """
    distribution = Attribute("Distribution")
    team = Attribute("Team")

    def __getitem__(release):
        """retrieve team by release"""

    def __iter__():
        """retrieve an iterator"""

class IDistroReleaseTeamApp(Interface):
    """A DistroRelease People Tag """
    release= Attribute("Release")
    team = Attribute("Team")


# it is deprecated BTW !!!
class ITeam(Interface):
     """auxiliar object to receive STUB person"""
     displayname = Attribute("name")
     role = Attribute("role")


# they didn't work as expected. spiv: help :)
class IDistroReleaseRole(Interface):
    """A DistroReleaseRole Object """
    release= Attribute("Release")
    person = Attribute("Person")
    role = Attribute("Role")

class IDistributionRole(Interface):
    """A Distribution Role Object"""
    distribution = Attribute("Distribution")
    person = Attribute("Person")
    role = Attribute("Role")

#########################################

class IPeopleApp(Interface):
    """A People Tag """

    def __getitem__(release):
        """retrieve personal by name"""

    def __iter__():
        """retrieve an iterator"""


class IPersonApp(Interface):
    """A Person Tag """
    person = Attribute("Person entry")
    id = Attribute("Person entry")


###########################################        

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
    cvsmodule = Attribute("duh")
    cvstarfile = Attribute("duh")
    branchfrom = Attribute("duh")
    svnrepository = Attribute("duh")
    archarchive = Attribute("the target archive")
    category = Attribute("duh")
    branchto = Attribute("duh")
    archversion = Attribute("duh")
    archsourcegpgkeyid = Attribute("duh")
    archsourcename = Attribute("duh")
    archsourceurl = Attribute("duh")
    def canChangeProduct():
        """is this sync allowed to have its product changed?"""
    def changeProduct(product):
        """change the product this sync belongs to to be 'product'"""
    product=Attribute ("a product backlink for this sync")

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

class IPackagePublishing(Interface):
    binarypackage = Attribute("BinaryPackage")
    distroarchrelease = Attribute("Distro Arch Relese")
    packages = Attribute("XXX")

class IBinaryPackage(Interface):
    """A binary package, e.g apache-utils"""
    # See the BinaryPackage table
    binarypackagename = Attribute("Binary Package Name")
    shortdesc = Attribute("Short Description")
    description = Attribute("Full Description")

class IBinaryPackageName(Interface):
    """A binary package name"""
    name = Attribute("Binary Package Name")

class IBinaryPackageBuild(Interface):
    """A binary package build, e.g apache-utils 2.0.48-4_i386"""
    # See the BinaryPackageBuild table
    
    version = Attribute("A version string")
    maintainer = Attribute("Maintainer")
    sourcePackageRelease = Attribute("An ISourcePackageRelease")
    sourcepackage = Attribute("An ISourcePackage")
    binaryPackage = Attribute("An ISourcePackageRelease")
    processor = Attribute("An ISourcePackageRelease")
    binpackageformat = Attribute("An ISourcePackageRelease")
    datebuilt = Attribute("An ISourcePackageRelease")

class ISourcePackage(Interface):
    """A source package, e.g apache-utils"""
    # See the SourcePackage table

    maintainer = Attribute("Maintainer")
    name = Attribute("A string")
    title = Attribute("Package Title")
    description = Attribute("Package Description")
    ##releases = Attribute("List of ISourcePackageRelease objects")
    proposed = Attribute("A source package release with upload status of "
                         "PROPOSED, else None")

class ISourcePackageRelease(Interface):
    """A source package release, e.g. apache-utils 2.0.48-3"""
    # See the SourcePackageRelease table

    version = Attribute("A version string")
    creator = Attribute("Person that created this release")
    sourcepackage = Attribute("The source package this is a release for")

    def branches():
        """Return the list of branches in a source package release"""


class ISoyuzPerson(Interface):
    """A person"""
    # use id instead unique name
    id = Attribute("ID for a person")
    givenname = Attribute("Given name")
    familyname = Attribute("Family name")
    displayname = Attribute("Display name")


class IManifestEntry(Interface):
    """"""
    branch = Attribute("A branch")


class IBranch(Interface):
    """A branch of some source code"""

    changesets = Attribute("List of changesets in a branch")


class IChangeset(Interface):
    """A changeset"""

    message = Attribute("The log message for this changeset")

##Dummy Interfaces
class IcurrentVersion(Interface):
    currentversion = Attribute("DUMMY")
    currentbuilds = Attribute("DUMMY")


# arch-tag: 3f98fde9-9a5b-447b-93e7-e4a9c770ca63
