
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
    entries = Attribute('number of distributions')
    
    def __getitem__(name):
        """retrieve distribution by name"""

    def distributions():
        """retrieve all Distribution"""

    def new(name, title, description, url):
        """Creates a new distribution with the given name.

        Returns that project.
        """
    
class IDistroApp(Interface):
    distribution = Attribute("Distribution")
    releases = Attribute("Distribution releases")
    enable_releases = Attribute("Enable Distribution releases Features")
    
    def getReleaseContainer(name):
        """Returns an associated IReleaseContainer"""


class IDistribution(Interface):
    """A Distribution Object"""
    id = Attribute("The distro's unique number.")
    name = Attribute("The distro's name.")
    title = Attribute("The distro's title.")
    description = Attribute("The distro's description.")
    domainname = Attribute("The distro's domain name.")
    owner = Attribute("The distro's owner.")



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

    def findPackagesByName():
        """Find packages by name."""

    def sourcePackagesBatch():
        """Return a batch of source packages."""

    
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
    builddepends = Attribute("Builddepends for this sourcepackagerelease")
    builddependsindep = Attribute("BuilddependsIndep for this sourcepackagerelease")
    distroreleasename = Attribute("The Distro Release name need to make links to bin packages")

    def __getitem__(name):
        """Retrieve a package release build by arch."""

class IbuilddepsContainer(Interface):
    name = Attribute("Package name for a builddepends/builddependsindep")
    signal = Attribute("Dependence Signal e.g = >= <= <")
    version = Attribute("Package version for a builddepends/builddependsindep")

class IDistroReleaseApp(Interface):
    """A Release Proxy """
    release = Attribute("Release")
    roles = Attribute("Release Roles")

    def getPackageContainer(name):
        """ Returns the associated IPackageSet """

    def findSourcesByName(name):
        """Returns The Release SourcePackages by name"""

    def findBinariesByName(name):
        """Returns The Release BianriesPackages by name"""

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

    def findPackagesByName():
        """Find packages by name"""


class IDistroReleaseBinaryReleaseBuildApp(Interface):
    binarypackagerelease = Attribute("Release")
    version = Attribute("Version")
    arch = Attribute("Arch")



class IDistroReleaseBinaryReleaseApp(Interface):
    """A Binary Release Proxy """
    binarypackagerelease = Attribute("BinaryPackageRelease")
    version = Attribute("BinaryPackageRelease Version ?!?!")
    sourcedistrorelease = Attribute("The DistroRelease from where the binary's SourcePackageRelease came from")
    archs = Attribute("Builded archs")
    
    def __getitem__(name):
        """retrieve binarypackagesbuild by version"""


class IDistroReleaseBinaryApp(Interface):    
    """A Binary Package Proxy """
    binarypackage = Attribute("BinaryPackage")
    lastversions = Attribute("Last Release Versions")
    currentversions = Attribute("Current Release Versions")
    release = Attribute("Distro Release")

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

class IDistroReleaseRole(Interface):
    """A DistroReleaseRole Object """
    distrorelease= Attribute("Release")
    person = Attribute("Person")
    role = Attribute("Role")
    rolename = Attribute("Rolename")
    
class IDistributionRole(Interface):
    """A Distribution Role Object"""
    distribution = Attribute("Distribution")
    person = Attribute("Person")
    role = Attribute("Role")
    rolename = Attribute("Rolename")

class IPeopleApp(Interface):
    """A People Tag """
    p_entries = Attribute("Number of person entries")
    t_entries = Attribute("Number of teams entries")

    def __getitem__(release):
        """retrieve personal by name"""

    def __iter__():
        """retrieve an iterator"""


class IPersonApp(Interface):
    """A Person Tag """
    person = Attribute("Person entry")
    id = Attribute("Person entry")
    email = Attribute("Email")
    wiki = Attribute("Wiki")
    jabber = Attribute("Jabber")
    irc = Attribute("IRC")    
    archuser = Attribute("Arch user")    
    gpg = Attribute("GPG")

    members = Attribute("Members of a Team")
    teams = Attribute("Team which I'm a member")
    subteams = Attribute("Sub Teams")
    distroroles = Attribute("Distribution Roles")
    distroreleaseroles = Attribute("Distrorelase Roles")

    packages = Attribute("A Selection of SourcePackageReleases")

    roleset = Attribute("Possible Roles")
    statusset = Attribute("Possible Status")

# new people related table interfaces
class ISoyuzEmailAddress(Interface):
    """Email aka our unique name"""
    person = Attribute("Owner")
    email = Attribute("Email")
    status = Attribute("Status")
    statusname = Attribute("StatusName")

class IGPGKey(Interface):
    """GPG support"""
    person = Attribute("Owner")
    keyid = Attribute("KeyID")
    pubkey = Attribute("Pub Key itself")
    fingerprint = Attribute("User Fingerprint")
    revoked = Attribute("Revoked")
    algorithm = Attribute("Algorithm")
    keysize = Attribute("Keysize")

class IArchUserID(Interface):
    """ARCH specific user ID """
    person = Attribute("Owner")
    archuserid = Attribute("ARCH user ID")

class IWikiName(Interface):
    """Wiki for Users"""
    person = Attribute("Owner")
    wiki = Attribute("wiki host")
    wikiname = Attribute("wikiname for user")

class IJabberID(Interface):
    """Jabber specific user ID """
    person = Attribute("Owner")
    jabberid = Attribute("Jabber user ID")

class IIrcID(Interface):
    """Wiki for Users"""
    person = Attribute("Owner")
    network = Attribute("IRC host")
    nickname = Attribute("nickname for user")

class IMembership(Interface):
    """Membership for Users"""
    person = Attribute("Owner")
    team = Attribute("Team")
    role= Attribute("Role on Team")
    status= Attribute("Status of this Relation")
    rolename = Attribute("Role Name")
    statusname = Attribute("Status Name")
    
class ITeamParticipation(Interface):
    """Team Participation for Users"""
    person = Attribute("Owner")
    team = Attribute("Team")

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
    parentrelease = Attribute("Parent Release")
    owner =Attribute("Owner")
    sourcecount = Attribute("Source Packages Counter")
    binarycount = Attribute("Binary Packages Counter")
    state = Attribute("DistroRelease Status")
    parent = Attribute("DistroRelease Parent")
    displayname = Attribute("Distrorelease Displayname")

################################################################
   
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
    def autosync():
        """enable this sync for automatic syncs"""
    def autosyncing():
        """is the sync enabled for automatic syncs?"""
    def canChangeProduct():
        """is this sync allowed to have its product changed?"""
    def changeProduct(product):
        """change the product this sync belongs to to be 'product'"""
    product=Attribute ("a product backlink for this sync")
    def enable():
        """enable this sync"""
    def enabled():
        """is the sync enabled?"""
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

class IBuild(Interface):
    """A Build interface"""
    distroarchrelease = Attribute("The Ditro Arch Release")
    component = Attribute("The BinaryPackage Component")
    section = Attribute("The BinaryPackage Section")
    sourcepackagerelease = Attribute("Sourcepackagerelease reference")
    
class IBinaryPackage(Interface):
    """A binary package, e.g apache-utils"""
    # See the BinaryPackage table
    binarypackagename = Attribute("Binary Package Name ID")
    sourcepackagerelease = Attribute("Sourcepackagerelease from where the binary comes")
    version = Attribute("Binary Package Version")
    shortdesc = Attribute("Short Description")
    description = Attribute("Full Description")
    build = Attribute("Binary Package Build")
    name = Attribute("Binary Package Name")

    component = Attribute("The BinaryPackage Component")
    section = Attribute("The BinaryPackage")

    pkgpriority = Attribute("Package Priority")

    licence = Attribute("Package Licence")
    
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
    shortdesc = Attribute("Package Shortdesc")
    description = Attribute("Package Description")
    distro = Attribute("Package Distribution")
    ##releases = Attribute("List of ISourcePackageRelease objects")
    proposed = Attribute("A source package release with upload status of "
                         "PROPOSED, else None")
    product = Attribute("A Product, or None")

class ISourcePackageRelease(Interface):
    """A source package release, e.g. apache-utils 2.0.48-3"""
    # See the SourcePackageRelease table

    sourcepackage = Attribute("The source package this is a release for")
    srcpackageformat = Attribute("Source Package Format")
    creator = Attribute("Person that created this release")
    version = Attribute("A version string")
    dateuploaded = Attribute("Date of Upload")
    urgency = Attribute("Source Package Urgency")
    dscsigningkey = Attribute("DSC Signing Key")
    component = Attribute("Source Package Component")
    changelog = Attribute("Source Package Change Log")
    pkgurgency = Attribute("Source Package Urgency Translated using dbschema")

    binaries = Attribute("Binary Packages generated by this SourcePackageRelease")
    
    def branches():
        """Return the list of branches in a source package release"""

class IComponent(Interface):
    name = Attribute("The Component Name")

class ISection(Interface):
    name = Attribute("The Section Name")

class ISoyuzPerson(Interface):
    """A person"""
    # use id instead unique name
    id = Attribute("ID for a person")
    givenname = Attribute("Given name")
    familyname = Attribute("Family name")
    displayname = Attribute("Display name")
    teamowner = Attribute("The Team Owner") 
    teamdescription = Attribute("The Team Description")
    karma = Attribute("Karma")
    karmatimestamp = Attribute("Karma Time stamp")
    password = Attribute("Password")
    name = Attribute("Login or Nick")
    
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
class ICurrentVersion(Interface):
    release = Attribute("The binary or source release object")
    currentversion = Attribute("Current version of A binary or source package")
    currentbuilds = Attribute("The current builds for binary or source package")


