/*
 * Hauge amounts of comments
 */

-- SourcePackage

COMMENT ON TABLE SourcePackage IS 'SourcePackage: A soyuz source package representation. This table represents the presence of a given source package in a distribution. It gives no indication of what distrorelease a package may be in.';
COMMENT ON COLUMN SourcePackage.maintainer IS 'The maintainer of a sourcepackage in a given distribution.';
COMMENT ON COLUMN SourcePackage.shortdesc IS 'The title or short name of a sourcepackage. E.g. "Mozilla Firefox Browser"';
COMMENT ON COLUMN SourcePackage.description IS 'A description of the sourcepackage. Typically longer and more detailed than shortdesc.';
COMMENT ON COLUMN SourcePackage.manifest IS 'The head HCT manifest for the sourcepackage';
COMMENT ON COLUMN SourcePackage.distro IS 'The distribution (if any) that the sourcepackage resides in.';

-- SourcePackageRelease

COMMENT ON TABLE SourcePackageRelease IS 'SourcePackageRelease: A soyuz source package release. This table represents a given release of a source package. Source package releases may be published into a distrorelease if relevant.';
COMMENT ON COLUMN SourcePackageRelease.sourcepackage IS 'The sourcepackage related to this release.';
COMMENT ON COLUMN SourcePackageRelease.creator IS 'The creator of this sourcepackagerelease. I.E. the person who uploaded the release.';
COMMENT ON COLUMN SourcePackageRelease.version IS 'The version string for this release. E.g. "1.0-2" or "1.4-5ubuntu9.1"';
COMMENT ON COLUMN SourcePackageRelease.dateuploaded IS 'The date/time that this sourcepackagerelease was uploaded to soyuz';
COMMENT ON COLUMN SourcePackageRelease.urgency IS 'The urgency of the upload. This is generally used to prioritise buildd activity but may also be used for "testing" systems or security work in the future';
COMMENT ON COLUMN SourcePackageRelease.dscsigningkey IS 'The GPG key used to sign the DSC. This is not necessarily the maintainer\'s key, the creator\'s key if for example a sponsor uploaded the package.';
COMMENT ON COLUMN SourcePackageRelease.component IS 'The component in which this sourcepackagerelease is meant to reside. E.g. main, universe, restricted';
COMMENT ON COLUMN SourcePackageRelease.changelog IS 'The changelog entries relevant to this sourcepackagerelease';
COMMENT ON COLUMN SourcePackageRelease.builddepends IS 'The build dependencies for this sourcepackagerelease';
COMMENT ON COLUMN SourcePackageRelease.builddependsindep IS 'The architecture-independant build dependancies for the sourcepackagerelease';
COMMENT ON COLUMN SourcePackageRelease.architecturehintlist IS 'The architectures which this sourcepackagerelease believes it should be built on. This is used as a hint to the buildds when looking for work to do.';
COMMENT ON COLUMN SourcePackageRelease.dsc IS 'The "Debian source control" file for the sourcepackagerelease. (*OBSOLETE* ???)';

-- SourcePackageName

COMMENT ON TABLE SourcePackageName IS 'SourcePackageName: A soyuz source package name.';

-- BinaryPackage

COMMENT ON TABLE BinaryPackage IS 'BinaryPackage: A soyuz binary package representation. This table stores the records for each binary package uploaded into the system. Each sourcepackagerelease may build various binarypackages on various architectures.';
COMMENT ON COLUMN BinaryPackage.binarypackagename IS 'A reference to the name of the binary package';
COMMENT ON COLUMN BinaryPackage.version IS 'The version of the binary package. E.g. "1.0-2"';
COMMENT ON COLUMN BinaryPackage.shortdesc IS 'A short description of the binary package. Commonly used on listings of binary packages';
COMMENT ON COLUMN BinaryPackage.description IS 'A longer more detailed description of the binary package';
COMMENT ON COLUMN BinaryPackage.build IS 'The build in which this binarypackage was produced';
COMMENT ON COLUMN BinaryPackage.binpackageformat IS 'The binarypackage format. E.g. RPM, DEB etc';
COMMENT ON COLUMN BinaryPackage.component IS 'The archive component that this binarypackage is in. E.g. main, universe etc';
COMMENT ON COLUMN BinaryPackage.section IS 'The archive section that this binarypackage is in. E.g. devel, libdevel, editors';
COMMENT ON COLUMN BinaryPackage.priority IS 'The priority that this package has. E.g. Base, Standard, Extra, Optional';
COMMENT ON COLUMN BinaryPackage.shlibdeps IS 'The shared library dependencies of this binary package';
COMMENT ON COLUMN BinaryPackage.depends IS 'The list of packages this binarypackage depends on';
COMMENT ON COLUMN BinaryPackage.recommends IS 'The list of packages this binarypackage recommends. Recommended packages often enhance the behaviour of a package.';
COMMENT ON COLUMN BinaryPackage.suggests IS 'The list of packages this binarypackage suggests.';
COMMENT ON COLUMN BinaryPackage.conflicts IS 'The list of packages this binarypackage conflicts with.';
COMMENT ON COLUMN BinaryPackage.replaces IS 'The list of packages this binarypackage replaces files in. Often this is used to provide an upgrade path between two binarypackages of different names';
COMMENT ON COLUMN BinaryPackage.provides IS 'The list of virtual packages (or real packages under some circumstances) which this binarypackage provides.';
COMMENT ON COLUMN BinaryPackage.essential IS 'Whether or not this binarypackage is essential to the smooth operation of a base system';
COMMENT ON COLUMN BinaryPackage.installedsize IS 'What the installed size of the binarypackage is. This is represented as a number of kilobytes of storage.';
COMMENT ON COLUMN BinaryPackage.copyright IS 'The copyright associated with this binarypackage. Often in the case of debian packages this is found in /usr/share/doc/<binarypackagename>/copyright';
COMMENT ON COLUMN BinaryPackage.licence IS 'The licence that this binarypackage is under.';


-- BinaryPackageFile

COMMENT ON TABLE BinaryPackageFile IS 'BinaryPackageFile: A soyuz <-> librarian link table. This table represents the ownership in the librarian of a file which represents a binary package';
COMMENT ON COLUMN BinaryPackageFile.binarypackage IS 'The binary package which is represented by the file';
COMMENT ON COLUMN BinaryPackageFile.libraryfile IS 'The file in the librarian which represents the package';
COMMENT ON COLUMN BinaryPackageFile.filetype IS 'The "type" of the file. E.g. DEB, RPM';

-- BinaryPackageName

COMMENT ON TABLE BinaryPackageName IS 'BinaryPackageName: A soyuz binary package name.';

-- OSFile

COMMENT ON TABLE OSFile IS 'OSFile: Soyuz\'s representation of files on disk. BinaryPackages put files in installations.';
COMMENT ON COLUMN OSFile.opath IS 'The filepath';


-- OSFileInPackage

COMMENT ON TABLE OSFileInPackage IS 'OSFileInPackage: Soyuz\'s representation of files in packages. This table stores the metadata associated with files which can be found in binarypackages.';
COMMENT ON COLUMN OSFileInPackage.osfile IS 'The OSFile (path) in question';
COMMENT ON COLUMN OSFileInPackage.binarypackage IS 'The binarypackage which contains this';
COMMENT ON COLUMN OSFileInPackage.unixperms IS 'The unix permissions assigned to the file';
COMMENT ON COLUMN OSFileInPackage.conffile IS 'Whether or not the file is a conffile in this package';
COMMENT ON COLUMN OSFileInPackage.createdoninstall IS 'Whether or not the file is created during the installation of the package on the system. It may also be used to store jeff''s mum''s pants';

-- Distribution

COMMENT ON TABLE Distribution IS 'Distribution: A soyuz distribution. A distribution is a collection of DistroReleases. Distributions often group together policy and may be referred to by a name such as "Ubuntu" or "Debian"';
COMMENT ON COLUMN Distribution.name IS 'The name of the distribution. Usually lower-case. E.g. "ubuntu" or "debian"';
COMMENT ON COLUMN Distribution.title IS 'The title of the distribution. More a "display name" as it were. E.g. "Ubuntu" or "Debian GNU/Linux"';
COMMENT ON COLUMN Distribution.description IS 'A description of the distribution. More detailed than the title, this column may also contain information about the project this distribution is run by.';
COMMENT ON COLUMN Distribution.domainname IS 'The domain name of the distribution. This may be used both for linking to the distribution and for context-related stuff.';
COMMENT ON COLUMN Distribution.owner IS 'The person in launchpad who is in ultimate-charge of this distribution within launchpad.';

-- DistroRelease

COMMENT ON TABLE DistroRelease IS 'DistroRelease: A soyuz distribution release. A DistroRelease is a given version of a distribution. E.g. "Warty" "Hoary" "Sarge" etc.';
COMMENT ON COLUMN DistroRelease.distribution IS 'The distribution which contains this distrorelease.';
COMMENT ON COLUMN DistroRelease.name IS 'The name of the distrorelease. This is usually a short name in lower case and would be used in sources.list configuration. E.g. "warty" "sarge" "sid"';
COMMENT ON COLUMN DistroRelease.title IS 'The display-name title of the distrorelease E.g. "Warty Warthog"';
COMMENT ON COLUMN DistroRelease.description IS 'The long detailed description of the release. This may describe the focus of the release or other related information.';
COMMENT ON COLUMN DistroRelease.version IS 'The version of the release. E.g. warty would be "4.10" and hoary would be "5.4"';
COMMENT ON COLUMN DistroRelease.components IS 'The components which are considered valid within this distrorelease.';
COMMENT ON COLUMN DistroRelease.sections IS 'The sections which are considered valid within this distrorelease.';
COMMENT ON COLUMN DistroRelease.releasestate IS 'The current state of this distrorelease. E.g. "pre-release freeze" or "released"';
COMMENT ON COLUMN DistroRelease.datereleased IS 'The date on which this distrorelease was released. (obviously only valid for released distributions)';
COMMENT ON COLUMN DistroRelease.parentrelease IS 'The parent release on which this distribution is based. This is related to the inheritance stuff.';
COMMENT ON COLUMN DistroRelease.owner IS 'The ultimate owner of this distrorelease.';

-- DistroArchRelease

COMMENT ON TABLE DistroArchRelease IS 'DistroArchRelease: A soyuz distribution release for a given architecture. A distrorelease runs on various architectures. The distroarchrelease groups that architecture-specific stuff.';
COMMENT ON COLUMN DistroArchRelease.distrorelease IS 'The distribution which this distroarchrelease is part of.';

-- DistributionRole

COMMENT ON TABLE DistributionRole IS 'DistributionRole: A soyuz distribution role. This table represents a role played by a specific person in a given distribution.';
COMMENT ON COLUMN DistributionRole.person IS 'The person undertaking the represented role.';
COMMENT ON COLUMN DistributionRole.distribution IS 'The distribution in which this role is undertaken';
COMMENT ON COLUMN DistributionRole.role IS 'The role that the identified person takes in the referenced distribution';

-- DistroReleaseRole

COMMENT ON TABLE DistroReleaseRole IS 'DistroReleaseRole: A soyuz distribution release role. This table represents a role played by a specific person in a specific distrorelease of a distribution.';
COMMENT ON COLUMN DistroReleaseRole.person IS 'The person undertaking the represented role.';
COMMENT ON COLUMN DistroReleaseRole.distrorelease IS 'The distrorelease in which the role is undertaken.';
COMMENT ON COLUMN DistroReleaseRole.role IS 'The role that the identified person undertakes in the referenced distrorelease.';

-- LibraryFileContent

COMMENT ON TABLE LibraryFileContent IS 'LibraryFileContent: A librarian file\'s contents. The librarian stores files in a safe and transactional way. This table represents the contents of those files within the database.';
COMMENT ON COLUMN LibraryFileContent.datecreated IS 'The date on which this librarian file was created';
COMMENT ON COLUMN LibraryFileContent.datemirrored IS '***FIXME***';
COMMENT ON COLUMN LibraryFileContent.filesize IS 'The size of the file';
COMMENT ON COLUMN LibraryFileContent.sha1 IS 'The SHA1 sum of the file\'s contents';

-- LibraryFileAlias

COMMENT ON TABLE LibraryFileAlias IS 'LibraryFileAlias: A librarian file\'s alias. The librarian stores, along with the file contents, a record stating the file name and mimetype. This table represents it.';
COMMENT ON COLUMN LibraryFileAlias.content IS 'The libraryfilecontent which is the data in this file.';
COMMENT ON COLUMN LibraryFileAlias.filename IS 'The name of the file. E.g. "foo_1.0-1_i386.deb"';
COMMENT ON COLUMN LibraryFileAlias.mimetype IS 'The mime type of the file. E.g. "application/x-debian-package"';

-- PackagePublishing

COMMENT ON TABLE PackagePublising IS 'PackagePublishing: Publishing records for Soyuz/Lucille. Lucille publishes binarypackages in distroarchreleases. This table represents the publishing of each binarypackage.';
COMMENT ON COLUMN PackagePublishing.binarypackage IS 'The binarypackage which is being published';
COMMENT ON COLUMN PackagePublishing.distroarchrelease IS 'The distroarchrelease in which the binarypackage is published';
COMMENT ON COLUMN PackagePublishing.component IS 'The component in which the binarypackage is published';
COMMENT ON COLUMN PackagePublishing.section IS 'The section in which the binarypackage is published';
COMMENT ON COLUMN PackagePublishing.priority IS 'The priority at which the binarypackage is published';
COMMENT ON COLUMN PackagePublishing.scheduleddeletiondate IS 'The datetime at which this publishing entry is scheduled to be removed from the distroarchrelease';
COMMENT ON COLUMN PackagePublishing.status IS 'The current status of the packagepublishing record. For example "PUBLISHED" "PENDING" or "PENDINGREMOVAL"';

-- SourcePackagePublishing

COMMENT ON TABLE SourcePackagePublishing IS 'SourcePackagePublishing: Publishing records for Soyuz/Lucille. Lucille publishes sourcepackagereleases in distroreleases. This table represents the publishing of each sourcepackagerelease.';
COMMENT ON COLUMN SourcePackagPublishing.distrorelease IS 'The distrorelease which is having the sourcepackagerelease being published into it.';
COMMENT ON COLUMN SourcePackagPublishing.sourcepackagerelease IS 'The sourcepackagerelease being published into the distrorelease.';
COMMENT ON COLUMN SourcePackagPublishing.status IS 'The current status of the sourcepackage publishing record. For example "PUBLISHED" "PENDING" or "PENDINGREMOVAL"';
COMMENT ON COLUMN SourcePackagPublishing.component IS 'The component in which the sourcepackagerelease is published';
COMMENT ON COLUMN SourcePackagPublishing.section IS 'The section in which the sourcepackagerelease is published';
COMMENT ON COLUMN SourcePackagPublishing.scheduleddeletiondate IS 'The datetime at which this publishing entry is scheduled to be removed from the distrorelease.';
COMMENT ON COLUMN SourcePackagPublishing.datepublished IS 'THIS COLUMN IS PROBABLY UNUSED';

-- SourcePackageRelationship

COMMENT ON TABLE SourcePackageRelationship IS 'SourcePackageRelationship: A soyuz relationship between sourcepackages. This table represents relationships between sourcepackages such as inheritance';
COMMENT ON COLUMN SourcePackageRelationship.subject IS 'The sourcepackage which acts as the subject in the sentence ''Package A <verbs> Package B''';
COMMENT ON COLUMN SourcePackageRelationship.label IS 'The verb in the sentence ''Package A <verbs> Package B'' E.g. ''derives from'' or ''effectively implements''';
COMMENT ON COLUMN SourcePackageRelationship.object IS 'The sourcepackage which acts as the object in the sentence ''Package A <verbs> Package B''';


-- SourcePackageReleaseFile

COMMENT ON TABLE SourcePackageReleaseFile IS 'SourcePackageReleaseFile: A soyuz source package release file. This table links sourcepackagerelease records to the files which comprise the input.';
COMMENT ON COLUMN SourcePackageReleaseFile.libraryfile IS 'The libraryfilealias embodying this file';
COMMENT ON COLUMN SourcePackageReleaseFile.filetype IS 'The type of the file. E.g. TAR, DIFF, DSC';
COMMENT ON COLUMN SourcePackageReleaseFile.sourcepackagerelease IS 'The sourcepackagerelease that this file belongs to';
