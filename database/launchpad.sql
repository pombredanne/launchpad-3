--
-- This will DESTROY your database and create a fresh one
--

/*

  TODO

        - re-evalutate some of the "text" field types, they might need to be "bytea"
	  unless we can guarantee utf-8
        - re-evaluate the relationship table names, see if there isn't a better name for each of them
	- add sample data for the schemas
	- make sure names are only [a-z][0-9][-.+] and can only start with [a-z]
	- set DEFAULT's for datestamps (now) and others
	- present the database as a set of Interfaces
        - add Series to products and projects
  CHANGES

  v0.95:
        - move bug priority from CodereleaseBug to SourcepackageBug
	- remove wontfix since it is now a bug priority ("wontfix")
	- add name to bugattachment
	- refactor bug attachments:
	  - don't have a relationship, each attachment on only one bug
	  - allow for revisions to attachments
	- rename BugRef to BugExternalref and remove bugref field
	- create a link ProjectBugsystem between Project's and BugSystem's
	- remove BugMessageSighting, each BugMessage now belongs to one and only one bug
	- add a nickname (optional unique name) to the Bug table
	- change the "summary" field of Bug to "title" for consistency
	- rename some tables:
	  - ReleaseBugStatus -> CodereleaseBug
	  - SourcepackageBugStatus -> SourcepackageBug
	  - ProductBugStatus -> ProductBug
        - add a createdate to project and product
  v0.94:
        - rename soyuz.sql to launchpad.sql
	- make Schema.extensible DEFAULT false (thanks spiv)
  v0.93:
        - add a manifest to Sourcepackage and Product, for the mutable HEAD manifest
	- add a manifest to Coderelease
	- rename includeas to entrytype in ManifestEntry
	- remove "part" from ManifestEntry
	- add hints in Manifest table so sourcerer knows how to name patch branches
	- fix my brain dead constraints for mutual exlcusivity on branch/changeset specs
	- for a ManifestEntry, branch AND changeset can now both be null, to allow for Scott's virtual entries
	- add the Packaging table to indicate the relationship between a Product and a Sourcepackage
  v0.92:
        - make Schema and Label have name, title, description
        - added filenames for UpstreamreleaseFile, SourcepackageFile and BinarypackageBuildFile
        - linked BinarypackageBuild to DistroRelease instead of DistroArchRelease
        - add the Country table for a list of countries
	- add the SpokenIn table to link countries and languages
        - rename TranslationProject to TranslationEffort
        - add iscurrent (boolean) field to the POTFiles table, current POTFiles
	    will be displayed in project summary pages.
        - add ChangesetFile, ChangesetFilename and ChangesetFileHash tables
        - rename Release to Coderelease (and all dependent tables)
        - refactor Processor and ProcessorFamily:
	  - the distroarchrelease now has a processorfamily field
	  - the binarypackagebuild (deb) now records its processor
	- refactor the allocation of binarypackagebuild's (debs) to distroarchrelease's
	  - create a new table BinarypackageUpload that stores the packagearchivestatus
	  - remove that status from the BinarypackageBuild table
	- refactor sourcepackage upload status
	  - move changes and urgency to sourcepackagerelease
	  - add builddependsindep so sourcepackagerelease

  v0.91:
        - remove Translation_POTFile_Relationship
	- ...and replace with a "project" field in POTFile
	- add a commenttext field to the POTMsgIDSighting table so we can track comments in POT files too

  v0.9:
         6 July 2004
       - first versioned release
*/

/*
  DESTROY ALL TABLES
*/
DROP TABLE PersonBug_Relationship;
DROP TABLE SpokenIn CASCADE;
DROP TABLE Country CASCADE;
DROP TABLE TranslationEffort_POTFile_Relationship CASCADE;
DROP TABLE POComment CASCADE;
DROP TABLE Branch_Relationship CASCADE;
DROP TABLE ProjectBugsystem CASCADE;
DROP TABLE BugSystem CASCADE;
DROP TABLE BugWatch CASCADE;
DROP TABLE RosettaPOTranslationSighting CASCADE;
DROP TABLE BugAttachment CASCADE;
DROP TABLE BugattachmentContent CASCADE;
DROP TABLE License CASCADE;
DROP TABLE Bug_Relationship CASCADE;
DROP TABLE BugMessage CASCADE;
DROP TABLE POTranslationSighting CASCADE;
DROP TABLE BugExternalref CASCADE;
DROP TABLE Bug CASCADE;
DROP TABLE Packaging CASCADE;
DROP TABLE SourcepackageReleaseFile CASCADE;
DROP TABLE Sourcepackage_Relationship CASCADE;
DROP TABLE SourcepackageRelease CASCADE;
DROP TABLE CodereleaseBug CASCADE;
DROP TABLE SourcepackageLabel CASCADE;
DROP TABLE SourcepackageBug CASCADE;
DROP TABLE Bug_Sourcepackage_Relationship CASCADE;
DROP TABLE SourcepackageUpload CASCADE;
DROP TABLE Sourcepackage CASCADE;
DROP TABLE BinarypackageBuildFile CASCADE;
DROP TABLE BinarypackageUpload CASCADE;
DROP TABLE BinarypackageBuild CASCADE;
DROP TABLE Binarypackage CASCADE;
DROP TABLE ProductBugStatus CASCADE;
DROP TABLE Branch CASCADE;
DROP TABLE ArchConfig CASCADE;
DROP TABLE ArchConfigEntry CASCADE;
DROP TABLE BugActivity CASCADE;
DROP TABLE ArchArchiveLocation CASCADE;
DROP TABLE POTranslation CASCADE;
DROP TABLE BugSystemType CASCADE;
DROP TABLE POTSubscription CASCADE;
DROP TABLE ChangesetFileHash CASCADE;
DROP TABLE ChangesetFile CASCADE;
DROP TABLE ChangesetFileName CASCADE;
DROP TABLE Changeset CASCADE;
DROP TABLE ArchArchive CASCADE;
DROP TABLE UpstreamReleaseFile CASCADE;
DROP TABLE UpstreamRelease CASCADE;
DROP TABLE Coderelease CASCADE;
DROP TABLE Coderelease_Relationship CASCADE;
DROP TABLE POTInheritance CASCADE;
DROP TABLE POTMsgIDSighting CASCADE;
DROP TABLE Manifest CASCADE;
DROP TABLE ProductLabel CASCADE;
DROP TABLE Product CASCADE;
DROP TABLE POFile CASCADE;
DROP TABLE POTFile CASCADE;
DROP TABLE Project_Relationship;
DROP TABLE POMsgID CASCADE;
DROP TABLE Language CASCADE;
DROP TABLE BugLabel CASCADE;
DROP TABLE TranslationEffort CASCADE;
DROP TABLE Project CASCADE;
DROP TABLE Project_TranslationEffort_Relationship CASCADE;
DROP TABLE Person CASCADE;
DROP TABLE EmailAddress CASCADE;
DROP TABLE TranslationFilter CASCADE;
DROP TABLE BranchLabel CASCADE;
DROP TABLE ManifestEntry CASCADE;
DROP TABLE GPGKey CASCADE;
DROP TABLE ArchUserID CASCADE;
DROP TABLE Membership CASCADE;
DROP TABLE WikiName CASCADE;
DROP TABLE JabberID CASCADE;
DROP TABLE IRCID CASCADE;
DROP TABLE PersonLabel CASCADE;
DROP TABLE TeamParticipation CASCADE;
DROP TABLE Schema CASCADE;
DROP TABLE Label CASCADE;
DROP TABLE Distribution CASCADE;
DROP TABLE DistroRelease CASCADE;
DROP TABLE DistroArchRelease CASCADE;
DROP TABLE ProcessorFamily CASCADE;
DROP TABLE Builder CASCADE;
DROP TABLE Processor CASCADE;
DROP TABLE SoyuzFileHash CASCADE;
DROP TABLE SoyuzFile CASCADE;
DROP TABLE OSFileInPackage CASCADE;
DROP TABLE OSFile;



/*
  Person
  This is a person in the Soyuz system. A Person can also be a
  team if the teamowner is not NULL. Note that we will create a
  Person entry whenever we see an email address we didn't know
  about, or a GPG key we didn't know about... and if we later
  link that to a real Soyuz person we will update all the tables
  that refer to that temporary person.

  A Person is one of these automatically created people if it
  has a NULL password and is not a team.
  
  It's created first so that a Schema can have an owner, we'll
  then define Schemas and Labels a bit later.
*/
CREATE TABLE Person (
  person                serial PRIMARY KEY,
  presentationname      text,
  givenname             text,
  familyname            text,
  password              text,
  teamowner             integer REFERENCES Person,
  teamdescription       text,
  karma                 integer,
  karmatimestamp        timestamp
);

INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Mark Shuttleworth', 'Mark', 'Shuttleworth' );     -- 1
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Dave Miller', 'David', 'Miller' );                -- 2
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Colin Watson', 'Colin', 'Watson' );               -- 3
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Steve Alexander', 'Steve', 'Alexander' );         -- 4
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Scott James Remnant', 'Scott James', 'Remnant' ); -- 5
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Robert Collins', 'Robert', 'Collins' );           -- 6


/*
  REVELATION. THE SOYUZ METADATA
*/


/*
  Schema
  This is the (finger finger) "metadata" (finger finger)
  which makes us... muahaha... distinctive... muahaha,
  muahahaha, muahahahahahaa....

  And yes, I'm not yet sure if my database model for this
  is on crack. Comments please. MS 24/06/04
*/
CREATE TABLE Schema (
  schema         serial PRIMARY KEY,
  name           text NOT NULL,
  title          text NOT NULL,
  description    text NOT NULL,
  owner          integer NOT NULL REFERENCES Person,
  extensible     boolean NOT NULL DEFAULT false
);



/*
  Label
  The set of labels in all schemas
*/
CREATE TABLE Label (
  label          serial PRIMARY KEY,
  schema         integer NOT NULL REFERENCES Schema,
  name           text NOT NULL,
  title          text NOT NULL,
  description    text NOT NULL
);




/*
  EmailAddress
  A table of email addresses for Soyuz people.
*/
CREATE TABLE EmailAddress (
  emailid     serial PRIMARY KEY,
  email       text NOT NULL UNIQUE,
  person      integer NOT NULL REFERENCES Person,
  label       integer NOT NULL REFERENCES Label
);



/*
  GPGKey
  A table of GPGKeys, mapping them to Soyuz users.
*/
CREATE TABLE GPGKey (
  gpgkey      serial PRIMARY KEY,
  person      integer NOT NULL REFERENCES Person,
  keyid       text NOT NULL UNIQUE,
  fingerprint text NOT NULL UNIQUE,
  pubkey      text NOT NULL,
  revoked     boolean NOT NULL
);



/*
  ArchUserID
  A table of Arch user id's
*/
CREATE TABLE ArchUserID (
  person     integer NOT NULL REFERENCES Person,
  archuserid text NOT NULL UNIQUE
);



/*
  WikiName
  The identity a person uses on one of the Soyuz wiki's.
*/
CREATE TABLE WikiName (
  person     integer NOT NULL REFERENCES Person,
  wiki       text NOT NULL,
  wikiname   text NOT NULL,
  UNIQUE ( wiki, wikiname )
);



/*
  JabberID
  A person's Jabber ID on our network.
*/
CREATE TABLE JabberID (
  person      integer NOT NULL REFERENCES Person,
  jabberid    text NOT NULL UNIQUE
);



/*
  IrcID
  A person's irc nick's.
*/
CREATE TABLE IRCID (
  person       integer NOT NULL REFERENCES Person,
  network      text NOT NULL,
  nickname     text NOT NULL
);




/*
  PersonLabel
  A neat way to attache tags to people...
*/
CREATE TABLE PersonLabel (
  person       integer NOT NULL REFERENCES Person,
  label        integer NOT NULL REFERENCES Label
);



/*
  Membership
  A table of memberships. It's only valid to have a membership
  in a team, not a non-team person.
*/
CREATE TABLE Membership (
  person      integer NOT NULL REFERENCES Person,
  team        integer NOT NULL REFERENCES Person,
  label       integer NOT NULL REFERENCES Label,
  status      integer NOT NULL REFERENCES Label,
  PRIMARY KEY ( person, team )
);



/*
  TeamParticipation
  This is a table which shows all the memberships
  of a person. Effectively it collapses team hierarchies
  and flattens them to a straight team-person relation.
  People are also members of themselves. This allows
  us to query against a person entry elsewhere in Soyuz
  and quickly find the things a person is an owner of.
*/
CREATE TABLE TeamParticipation (
  team         integer NOT NULL REFERENCES Person,
  person       integer NOT NULL REFERENCES Person,
  PRIMARY KEY ( team, person )
);



/*
  BUTTRESS. THE ARCH REPOSITORY.
  This is the Soyuz subsystem that handles the storing and
  cataloguing of all of our Arch branches.
*/



/*
  ArchArchive
  A table of all known Arch Archives.
*/
CREATE TABLE ArchArchive (
  archive       serial PRIMARY KEY,
  name          text NOT NULL,
  title         text NOT NULL,
  description   text NOT NULL,
  visible       boolean NOT NULL,
  owner         integer REFERENCES Person
);



/*
  ArchArchiveLocation
  A table of known Arch archive locations.
*/
CREATE TABLE ArchArchiveLocation (
  archive       integer NOT NULL REFERENCES ArchArchive,
  archivetype   integer NOT NULL, -- 0: readwrite, 1: readonly, 2: mirrortarget
  url           text NOT NULL,
  gpgsigned     boolean NOT NULL
);



/*
  Branch
  An Arch Branch in the Soyuz system.
*/
CREATE TABLE Branch (
  branch                 serial PRIMARY KEY,
  archive                integer NOT NULL REFERENCES ArchArchive,
  categorybranchversion  text NOT NULL,
  title                  text NOT NULL,
  description            text NOT NULL,
  visible                boolean NOT NULL,
  owner                  integer REFERENCES Person
);


/*
  Changeset
  An Arch changeset.
*/
CREATE TABLE Changeset (
  changeset      serial PRIMARY KEY,
  branch         integer NOT NULL REFERENCES Branch,
  createdate     timestamp NOT NULL,
  logmessage     text NOT NULL,
  author         integer REFERENCES Person,
  gpgkey         integer REFERENCES GPGKey
);



/*
  ChangesetFileName
  A filename in an arch changeset.
*/
CREATE TABLE ChangesetFileName (
  changesetfilename     serial PRIMARY KEY,
  filename              text NOT NULL UNIQUE
);



/*
  ChangesetFile
  A file in an arch changeset.
*/
CREATE TABLE ChangesetFile (
  changesetfile      serial PRIMARY KEY,
  changeset          integer NOT NULL REFERENCES Changeset,
  changesetfilename  integer NOT NULL REFERENCES ChangesetFileName,
  filecontents       bytea NOT NULL,
  filesize           integer NOT NULL,
  UNIQUE ( changeset, changesetfilename )
);



/*
  ChangesetFileHash
  A cryptographic hash of a changeset file.
*/
CREATE TABLE ChangesetFileHash (
  changesetfile     integer NOT NULL REFERENCES ChangesetFile,
  hashalg           integer NOT NULL REFERENCES Label,
  hash              bytea NOT NULL
);



/*
  Branch_Relationship
  A table of relationships between branches. For example:
  "src is a debianization-branch-of dst"
  "src is-a-patch-branch-of dst
*/
CREATE TABLE Branch_Relationship (
  src        integer NOT NULL REFERENCES Branch,
  dst        integer NOT NULL REFERENCES Branch,
  label      integer NOT NULL REFERENCES Label,
  PRIMARY KEY ( src, dst )
);




/*
  BranchLabel
  A table of labels on branches.
*/
CREATE TABLE BranchLabel (
  branch       int NOT NULL REFERENCES Branch,
  label        int NOT NULL REFERENCES Label
);




/*
  Manifest
  A release manifest. This is sort of an Arch config
  on steroids. A Manifest is a set of ManifestEntry's
*/
CREATE TABLE Manifest (
  manifest         serial PRIMARY KEY,
  creationdate     timestamp NOT NULL,
  brancharchive    integer REFERENCES ArchArchive, --
  branchcategory   text,                           -- Where to put new patch-branches
  branchversion    text                            --
);




/*
  ManifestEntry
  An entry in a Manifest. each entry specifies either a branch or
  a specific changeset (revision) on a branch, as well as how that
  piece of code (revision) is brought into the release.
*/
CREATE TABLE ManifestEntry (
  manifest        integer NOT NULL REFERENCES Manifest,
  sequence        integer NOT NULL,
  branch          integer REFERENCES Branch,
  changeset       integer REFERENCES Changeset,
  entrytype       integer NOT NULL REFERENCES Label,
  path            text NOT NULL,
  patchon         integer NOT NULL,
  -- sequence must be a positive integer
  CHECK ( sequence > 0 ),
  -- EITHER branch OR changeset:
  CHECK ( NOT ( branch IS NOT NULL AND changeset IS NOT NULL ) ),
  -- the "patchon" must be another manifestentry from the same
  -- manifest, and a different sequence
  -- XXX no idea how to express this constraint, help!
  -- the primary key is the combination of manifest and sequence
  PRIMARY KEY ( manifest, sequence )
);



/*
  FLOSS. THE OPEN SOURCE WORLD
  This is the Soyuz subsystem that models the open source world
  of projects and products.
*/


/*
 The Project table. This stores information about an open
 source project, which can be translated or packaged, or
 about which bugs can be filed.
*/
CREATE TABLE Project (
    project      serial PRIMARY KEY,
    owner        integer NOT NULL REFERENCES Person,
    name         text NOT NULL UNIQUE,
    title        text NOT NULL,
    description  text NOT NULL,
    createdate   timestamp NOT NULL,
    homepage     text
    );


/*
 The Project_Relationship table. This stores information about
 the relationships between open source projects. For example,
 the Gnome project aggregates the GnomeMeeting project.
*/
CREATE TABLE Project_Relationship (
  src           integer NOT NULL REFERENCES Project,
  dst           integer NOT NULL REFERENCES Project,
  relationship  text NOT NULL,
  value         text
);



/*
  Product
  A table of project products. A product is something that
  can be built, or a branch of code that is useful elsewhere, or
  a set of docs... some distinct entity. Products can be made
  up of other products, but that is not reflected in this
  database. For example, Firefax includes Gecko, both are
  products.
*/
CREATE TABLE Product (
  product       serial PRIMARY KEY,
  project       integer NOT NULL REFERENCES Project,
  owner         integer NOT NULL REFERENCES Person,
  name          text NOT NULL,
  title         text NOT NULL,
  description   text NOT NULL,
  createdate    timestamp NOT NULL,
  homepage      text,
  manifest      integer REFERENCES Manifest,
  UNIQUE ( project, name )
);



/*
  ProductLabel
  A label or metadata on a Product.
*/
CREATE TABLE ProductLabel (
  product  integer NOT NULL REFERENCES Product,
  label      integer NOT NULL REFERENCES Label,
  PRIMARY KEY ( product, label )
);



/*
  UpstreamRelease
  A specific tarball release of Upstream.
*/
CREATE TABLE UpstreamRelease (
  upstreamrelease  serial PRIMARY KEY,
  product        integer NOT NULL REFERENCES Product,
  releasedate      timestamp NOT NULL,
  name             text NOT NULL,
  gsvname          text,
  description      text,
  owner            integer REFERENCES Person
);


/*
   BUTTRESS phase 2
*/


/*
  ArchConfig
  A table to model Arch configs.
*/
CREATE TABLE ArchConfig (
  archconfig       serial PRIMARY KEY,
  name             text NOT NULL,
  title            text NOT NULL,
  description      text NOT NULL,
  upstreamrelease  integer REFERENCES UpstreamRelease,
  owner            integer REFERENCES Person
);



/*
  ArchConfigEntry
  A table to represent the entries in an Arch config. Each
  row is a separate entry in the arch config.
*/
CREATE TABLE ArchConfigEntry (
  archconfig    integer NOT NULL REFERENCES ArchConfig,
  path          text NOT NULL,
  branch        integer REFERENCES Branch,
  changeset     integer REFERENCES Changeset,
  -- EITHER branch OR changeset:
  CHECK ( NOT ( branch IS NULL AND changeset IS NULL ) ),
  CHECK ( NOT ( branch IS NOT NULL AND changeset IS NOT NULL ) )
);



/*
  LOGISTIX. THE PACKAGES AND DISTRIBUTION MANAGER.
  Nicknamed after UPS (United Parcel Service) this is the
  Soyuz subsystem that deals with distribution and packages.
*/



/*
  ProcessorFamily
  A family of CPU's, which are all compatible. In other words, code
  compiled for any one of these processors will run on any of the
  others.
*/
CREATE TABLE ProcessorFamily (
  processorfamily    serial PRIMARY KEY,
  name               text NOT NULL UNIQUE,
  title              text NOT NULL,
  description        text NOT NULL,
  owner              integer NOT NULL REFERENCES Person
);



/*
  Processor
  This is a table of system architectures. A DistroArchRelease needs
  to be one of these.
*/
CREATE TABLE Processor (
  processor          serial PRIMARY KEY,
  family             integer NOT NULL REFERENCES ProcessorFamily,
  name               text NOT NULL UNIQUE,
  title              text NOT NULL,
  description        text NOT NULL,
  owner              integer NOT NULL REFERENCES Person
);



/*
  Builder
  An Ubuntu build daemon.
*/
CREATE TABLE Builder (
  builder            serial PRIMARY KEY,
  processor          integer NOT NULL REFERENCES Processor,
  fqdn               text NOT NULL,
  name               text NOT NULL,
  title              text NOT NULL,
  description        integer NOT NULL REFERENCES Person,
  UNIQUE ( fqdn, name )
);



/*
  Distribution
  An open source distribution. Collection of packages, the reason
  for Soyuz existence.
*/
CREATE TABLE Distribution (
  distribution     serial PRIMARY KEY,
  name             text NOT NULL,
  title            text NOT NULL,
  description      text NOT NULL,
  components       integer NOT NULL REFERENCES Schema,
  sections         integer NOT NULL REFERENCES Schema,
  owner            integer NOT NULL REFERENCES Person
);



/*
  DistroRelease
  These are releases of the various distributions in the system. For
  example: warty, hoary, grumpy, woody, potato, slink, sarge, fc1,
  fc2.
*/
CREATE TABLE DistroRelease (
  distrorelease   serial PRIMARY KEY,
  distribution    integer NOT NULL REFERENCES Distribution,
  name            text NOT NULL, -- "warty"
  title           text NOT NULL, -- "Ubuntu 4.10 (The Warty Warthog Release)"
  description     text NOT NULL,
  version         text NOT NULL, -- "4.10"
  releasestate    integer NOT NULL REFERENCES Label
);




/*
  DistroArchRelease
  This is a distrorelease for a particular architecture, for example,
  warty-i386.
*/
CREATE TABLE DistroArchRelease (
  distroarchrelease serial PRIMARY KEY,
  distrorelease     integer NOT NULL REFERENCES DistroRelease,
  processor         integer NOT NULL REFERENCES Processor,
  architecturetag   text NOT NULL,
  releasestatus     integer NOT NULL REFERENCES Label,
  releasedate       timestamp,
  owner             integer NOT NULL REFERENCES Person
);



/*
  SoyuzFile
  The Soyuz system keeps copies of all the files that are used to make
  up a distribution, such as deb's and tarballs and .dsc files and .spec
  files and Coderelease files... these are represented by this table.
*/
CREATE TABLE SoyuzFile (
  soyuzfile        serial PRIMARY KEY,
  filename         text NOT NULL,
  filesize         integer NOT NULL
);



/*
  SoyuzFileHash
  A hash (cryptographic digest) on the file. We can support multiple
  different hashes with different algorithms. Initially we'll just 
  use SHA1, but if that gets broken we can trivially switch to another
  algorithm.

  The hash is not required to be UNIQUE but Oscar should flag duplicates
  for inspection by hand. Note that the combination of filesize and hash
  should be unique or there is something very weird going on. Or we just hit
  the crypto lottery and found a collision.
*/
CREATE TABLE SoyuzFileHash (
  soyuzfile       integer NOT NULL REFERENCES SoyuzFile,
  hashalg         integer NOT NULL REFERENCES Label,
  hash            bytea NOT NULL
);



/*
  UpstreamReleaseFile
  A file from an Upstream Coderelease. Usually this would be a tarball.
*/
CREATE TABLE UpstreamReleaseFile (
  upstreamrelease integer NOT NULL REFERENCES UpstreamRelease,
  soyuzfile       integer NOT NULL REFERENCES SoyuzFile,
  filetype        integer NOT NULL REFERENCES Label,
  filename        text NOT NULL
);



/*
  Sourcepackage
  A distribution source package. In RedHat or Debian this is the name
  of the source package, in Gentoo it's the Ebuild name.
*/
CREATE TABLE Sourcepackage (
  sourcepackage    serial PRIMARY KEY,
  maintainer       integer NOT NULL REFERENCES Person,
  name             text NOT NULL,
  title            text NOT NULL,
  description      text NOT NULL,
  manifest         integer REFERENCES Manifest
);



/*
  Sourcepackage_Relationship
  The relationship between two source packages. For example, if a source
  package in Ubuntu is derived from a source package in Debian, we would
  reflect that here.
*/
CREATE TABLE Sourcepackage_Relationship (
  src       integer NOT NULL REFERENCES Sourcepackage,
  dst       integer NOT NULL REFERENCES Sourcepackage,
  label     integer NOT NULL REFERENCES Sourcepackage,
  CHECK ( src <> dst )
);



/*
  SourcepackageLabel
  A tag or label on a source package.
*/
CREATE TABLE SourcepackageLabel (
  sourcepackage     integer NOT NULL REFERENCES Sourcepackage,
  label             integer NOT NULL REFERENCES Label
);




/*
  Packaging
  This is really the relationship between a Product and a
  Sourcepackage. For example, it allows us to say that
  the apache2 source package is a packaging of the
  httpd Product from the Apache Group.
*/
CREATE TABLE Packaging (
  product         integer NOT NULL REFERENCES Product,
  sourcepackage   integer NOT NULL REFERENCES Sourcepackage,
  label           integer NOT NULL REFERENCES Label
);




/*
  SourcepackageRelease
  A SourcepackageRelease is a specific release of a Sourcepackage, which is
  associated with one or more distribution releases. So apache2__2.0.48-3 can
  be in both ubuntu/warty and debian/sarge.
*/
CREATE TABLE SourcepackageRelease (
  sourcepackagerelease   serial PRIMARY KEY,
  sourcepackage          integer NOT NULL REFERENCES Sourcepackage,
  srcpackageformat       integer NOT NULL REFERENCES Label,
  creator                integer NOT NULL REFERENCES Person,
  version                text NOT NULL, -- "2.0.48-3"
  dateuploaded           timestamp NOT NULL,
  urgency                integer NOT NULL REFERENCES Label,
  dscsigningkey          integer REFERENCES GPGKey,
  component              integer REFERENCES Label,
  changelog              text,
  changes                text,
  builddepends           text,
  builddependsindep      text,
  architecturehintlist   text
);



/*
  SourcepackageReleaseFile
  A file associated with a sourcepackagerelease. For example, could be
  a .dsc file, or an orig.tar.gz, or a diff.gz...
*/
CREATE TABLE SourcepackageReleaseFile (
  sourcepackagerelease  integer NOT NULL REFERENCES SourcepackageRelease,
  soyuzfile             integer NOT NULL REFERENCES SoyuzFile,
  filetype              integer NOT NULL REFERENCES Label,
  filename              text NOT NULL
);



/*
  SourcepackageUpload
  This table indicates which sourcepackagereleases are present in a
  given distrorelease. It also indicates their status in that release
  (for example, whether or not that sourcepackagerelease has been
  withdrawn, or is currently published, in that archive).
*/
CREATE TABLE SourcepackageUpload (
  distrorelease          integer NOT NULL REFERENCES DistroRelease,
  sourcepackagerelease   integer NOT NULL REFERENCES SourcepackageRelease,
  packagereleasestatus   integer NOT NULL REFERENCES Label,
  PRIMARY KEY ( distrorelease, sourcepackagerelease )
);



/*
  Binarypackage
  This is a binary package... not an actual built package (that
  is a BinarypackageBuild) but the concept of that binary package.
  It stores the name of the binary package, together with other
  details. Note that different distributions might well have
  different binary packages with the same name. In fact, a single
  distribution might have binary packages with the same name at
  different times, that have entirely different source packages
  and hence maintainers.
*/
CREATE TABLE Binarypackage (
  binarypackage    serial PRIMARY KEY,
  name             text NOT NULL,
  title            text NOT NULL,
  description      text NOT NULL
);




/*
  BinarypackageBuild
  This is an actual package, built on a specific architecture,
  ready for installation.
*/
CREATE TABLE BinarypackageBuild (
  binarypackagebuild     serial PRIMARY KEY,
  sourcepackagerelease   integer NOT NULL REFERENCES SourcepackageRelease,
  binarypackage          integer NOT NULL REFERENCES Binarypackage,
  processor              integer NOT NULL REFERENCES Processor,
  binpackageformat       integer NOT NULL REFERENCES Label,
  version                text NOT NULL,
  builddate              timestamp NOT NULL,
  gpgsigningkey          integer REFERENCES GPGKey,
  component              integer REFERENCES Label,
  section                integer REFERENCES Label,
  shlibdeps              text,
  depends                text,
  recommends             text,
  suggests               text,
  conflicts              text,
  replaces               text,
  provides               text,
  essential              boolean,
  installedsize          integer
);



/*
  BinarypackageBuildFile
  This is a file associated with a built binary package. Could
  be a .deb or an rpm, or something similar from a gentoo box.
*/
CREATE TABLE BinarypackageBuildFile (
  binarypackagebuild     integer NOT NULL REFERENCES BinarypackageBuild,
  soyuzfile              integer NOT NULL REFERENCES SoyuzFile,
  filetype               integer NOT NULL REFERENCES Label,
  filename               text NOT NULL
);



/*
  BinarypackageUpload
  This table records the status of a binarypackagebuild (deb) in a
  distrorelease (woody)
*/
CREATE TABLE BinarypackageUpload (
  binarypackagebuild     integer NOT NULL REFERENCES BinarypackageBuild,
  distrorelease          integer NOT NULL REFERENCES DistroRelease,
  packagestatus          integer NOT NULL REFERENCES Label
);




/*
  LIBRARIAN. TRACKING UPSTREAM AND SOURCE PACKAGE RELEASES.
  This section is devoted to data that tracks upstream and distribution
  SOURCE PACKAGE releases. So, for example, Apache 2.0.48 is an
  UpstreamRelease. Apache 2.0.48-3 is a Debian SourcepackageRelease.
  We have data tables for both of those, and the Coderelease table is
  the data that is common to any kind of Coderelease. This subsystem also
  keeps track of the actual files associated with Codereleases, such as
  tarballs and deb's and .dsc files and changelog files...
*/



/*
  Coderelease
  A release of software. Could be an Upstream release or
  a SourcepackageRelease.
*/
CREATE TABLE Coderelease (
  coderelease          serial PRIMARY KEY,
  upstreamrelease      integer REFERENCES UpstreamRelease,
  sourcepackagerelease integer REFERENCES SourcepackageRelease,
  manifest             integer REFERENCES Manifest,
  CHECK ( NOT ( upstreamrelease IS NULL AND sourcepackagerelease IS NULL ) ),
  CHECK ( NOT ( upstreamrelease IS NOT NULL AND sourcepackagerelease IS NOT NULL ) )
); -- EITHER upstreamrelease OR sourcepackagerelease must not be NULL



/*
  Coderelease_Relationship
  Maps the relationships between releases (upstream and
  sourcepackage).
*/
CREATE TABLE Coderelease_Relationship (
  src       integer NOT NULL REFERENCES Coderelease,
  dst       integer NOT NULL REFERENCES Coderelease,
  label     integer NOT NULL REFERENCES Label,
  PRIMARY KEY ( src, dst )
);




/*
  OSFile
  This is a file in one of the OS's managed in Soyuz.
*/
CREATE TABLE OSFile (
  osfile    serial PRIMARY KEY,
  path      text NOT NULL UNIQUE
);



/*
  OSFileInPackage
  This table tells us all the files that are in a given binary package
  build. It also includes information about the files, such as their
  unix permissions, and whether or not they are a conf file.
*/
CREATE TABLE OSFileInPackage (
  osfile               integer NOT NULL REFERENCES OSFile,
  binarypackagebuild   integer NOT NULL REFERENCES BinarypackageBuild,
  unixperms            integer NOT NULL,
  conffile             boolean NOT NULL,
  createdby            boolean NOT NULL
);



/*
  ROSETTA. THE TRANSLATION SUPER-PORTAL
  This is the Soyuz subsystem that coordinates and manages
  the translation of open source software and documentation.
*/



/*
  TranslationFilter
  A set of "sunglasses" through which we see translations. We only want
  to see translations that are compatible with this filter in terms
  of licence, review and contribution criteria. This will not be
  implemented in Rosetta v1.0
*/
CREATE TABLE TranslationFilter (
  translationfilter serial PRIMARY KEY,
  owner             integer NOT NULL REFERENCES Person,
  title             text,
  description       text
);



/*
 The TranslationEffort table. Stores information about each active
 translation effort. Note, a translationeffort is an aggregation of
 works. For example, the Gnome Translation Project, which aims to
 translate the PO files for many gnome applications. This is a point
 for the translation team to rally around.
*/
CREATE TABLE TranslationEffort (
  translationeffort     serial PRIMARY KEY,
  owner                 integer NOT NULL REFERENCES Person,
  title                 text NOT NULL,
  description           text NOT NULL,
  translationfilter     integer REFERENCES TranslationFilter
);




/*
  Project_TranslationEffort_Relationship
  Maps the way a translation project is related to an open source
  project.
*/
CREATE TABLE Project_TranslationEffort_Relationship (
  project             integer NOT NULL REFERENCES Project,
  translationeffort   integer NOT NULL REFERENCES TranslationEffort,
  label               integer NOT NULL REFERENCES Label,
  PRIMARY KEY ( project, translationeffort )
);




/*
  POTInheritance
  A handle on an inheritance sequence for POT files.
*/
CREATE TABLE POTInheritance (
  potinheritance        serial PRIMARY KEY,
  title                 text,
  description           text
);



/*
  License
  A license. We need quite a bit more in the long term
  to track licence compatibility etc.
*/
CREATE TABLE License (
  license               serial PRIMARY KEY,
  legalese              text NOT NULL
);


/*
  POTFile
  A PO Template File, which is the first thing that Rosetta will set
  about translating.
*/
CREATE TABLE POTFile (
  potfile               serial PRIMARY KEY,
  project               integer NOT NULL REFERENCES Project,
  branch                integer REFERENCES Branch,
  changeset             integer REFERENCES Changeset,
  name                  text NOT NULL UNIQUE,
  title                 text NOT NULL,
  description           text NOT NULL,
  copyright             text NOT NULL,
  license               integer NOT NULL REFERENCES License,
  datecreated           timestamp NOT NULL,
  path                  text NOT NULL,
  iscurrent             boolean NOT NULL,
  defaultinheritance    integer REFERENCES POTInheritance,
  defaultfilter         integer REFERENCES TranslationFilter,
  owner                 integer REFERENCES Person,
  -- EITHER branch OR changeset:
  CHECK ( NOT ( branch IS NULL AND changeset IS NULL ) ),
  CHECK ( NOT ( branch IS NOT NULL AND changeset IS NOT NULL ) )
);



/*
  POMsgID
  A PO or POT File MessageID
*/
CREATE TABLE POMsgID (
  pomsgid              serial PRIMARY KEY,
  msgid                text UNIQUE
);



/*
  POTranslation
  A PO translation. This is just a piece of text, where the
  "translation" might in fact be the original language.
*/
CREATE TABLE POTranslation (
  potranslation         serial PRIMARY KEY,
  text                  text
);



/*
  Language
  A table of languages, for Rosetta.
*/
CREATE TABLE Language (
  language              serial PRIMARY KEY,
  code                  text NOT NULL UNIQUE,
  englishname           text,
  nativename            text
);




/*
  Country
  A list of countries.
*/
CREATE TABLE Country (
  country             serial PRIMARY KEY,
  iso3166code2        text NOT NULL,
  iso3166code3        text NOT NULL,
  name                text NOT NULL,
  title               text NOT NULL,
  description         text NOT NULL
);



/*
  SpokenIn
  A table linking countries the languages spoken in them.
*/
CREATE TABLE SpokenIn (
  language           integer NOT NULL REFERENCES Language,
  country            integer NOT NULL REFERENCES Country,
  PRIMARY KEY ( language, country )
);



/*
  POFile
  A PO File. This is a language-specific set of translations.
*/
CREATE TABLE POFile (
  pofile               serial PRIMARY KEY,
  potfile              integer NOT NULL REFERENCES POTFile,
  language             integer NOT NULL REFERENCES Language,
  title                text,
  description          text,
  topcomment           text,  -- the comment at the top of the file
  header               text,  -- the contents of the NULL msgstr
  lasttranslator       integer REFERENCES Person,
  license              integer REFERENCES License,
  completeness         integer  -- between 0 and 100
);



/*
  POTMsgIDSighting
  Table that documents the sighting of a particular msgid in a pot file.
*/
CREATE TABLE POTMsgIDSighting (
  potfile             integer NOT NULL REFERENCES POTFile,
  pomsgid             integer NOT NULL REFERENCES POMsgID,
  firstseen           timestamp NOT NULL,
  lastseen            timestamp NOT NULL,
  iscurrent           boolean NOT NULL,
  commenttext         text,
  singular            integer REFERENCES POMsgID, -- if this is not NULL then it's part of a tuple
  PRIMARY KEY ( potfile, pomsgid )
);



/*
  POTranslationSighting
  A sighting of a translation in a PO file IN REVISION CONTROL. This
  is contrasted with a RosettaPOTranslationSighting, which is a
  translation given to us for a potfile/language.
*/
CREATE TABLE POTranslationSighting (
  potranslationsighting serial PRIMARY KEY,
  pofile                integer NOT NULL REFERENCES POFile,
  pomsgid               integer NOT NULL REFERENCES POMsgID,
  potranslation         integer NOT NULL REFERENCES POTranslation,
  license               integer NOT NULL REFERENCES License,
  fuzzy                 boolean NOT NULL,
  rosettaprovided       boolean NOT NULL,
  firstseen             timestamp NOT NULL,
  lastseen              timestamp NOT NULL,
  iscurrent             boolean NOT NULL,
  commenttext           text,
  pluralform            integer,
  CHECK ( pluralform >= 0 )
);



/*
  RosettaPOTranslationSighting
  A record of a translation given to Rosetta through the web, or
  web service, or otherwise.
*/
CREATE TABLE RosettaPOTranslationSighting (
  rosettapotranslation serial PRIMARY KEY,
  person               integer NOT NULL REFERENCES Person,
  potfile              integer NOT NULL REFERENCES POTFile,
  pomsgid              integer NOT NULL REFERENCES POMsgID,
  language             integer NOT NULL REFERENCES Language,
  potranslation        integer NOT NULL REFERENCES POTranslation,
  license              integer NOT NULL REFERENCES License,
  dateprovided         timestamp NOT NULL,
  datetouched          timestamp NOT NULL,
  pluralform           integer,
  CHECK ( pluralform >= 0 )
);



/*
  POComment
  A table of comments provided by translators and the translation
  system (these are extracted from PO files as well as provided to
  us through the web and web services API).
*/
CREATE TABLE POComment (
  pocomment           serial PRIMARY KEY,
  potfile             integer NOT NULL REFERENCES POTFile,
  pomsgid             integer REFERENCES POMsgID,
  language            integer REFERENCES Language,
  potranslation       integer REFERENCES POTranslation,
  commenttext         text NOT NULL,
  date                timestamp NOT NULL,
  person              integer REFERENCES Person
);




/*
  TranslationEffort_POTFile_Relationship
  A translation project incorporates a POTfile that is under translation.
  The inheritance pointer allows this project to specify a custom
  translation inheritance sequence.
*/
CREATE TABLE TranslationEffort_POTFile_Relationship (
  translationeffort integer NOT NULL REFERENCES TranslationEffort ON DELETE CASCADE,
  potfile            integer NOT NULL REFERENCES POTFile,
  potinheritance     integer REFERENCES POTInheritance,
  UNIQUE (translationeffort , potfile)
);



/*
  Project_POTFile_Relationship
  Captures the relationship between a Project and a translated POTFile.
CREATE TABLE Project_POTFile_Relationship (
  project            integer NOT NULL REFERENCES Project,
  potfile            integer NOT NULL REFERENCES POTFile,
  label              integer NOT NULL REFERENCES Label
);
*/




/*
  POTSubscription
  Records the people who have subscribed to a POT File. They can
  subscribe to the POT file and get all the PO files, or just the PO
  files for a specific language.
*/
CREATE TABLE POTSubscription (
  potsubscription      serial PRIMARY KEY,
  person               integer NOT NULL REFERENCES Person,
  language             integer REFERENCES Language,
  notificationinterval interval NOT NULL,
  lastnotified         timestamp,
  potinheritance       integer REFERENCES POTInheritance,
  translationfilter    integer REFERENCES TranslationFilter
);



/*
  BOOGER. THE ISSUE TRACKING SYSTEM.
  This is the Soyuz subsystem that handled bugs and issue
  tracking for all the distributions we know about.
*/


/*
  Bug
  The core bug entry. A Booger.
*/
CREATE TABLE Bug (
  bug                     serial PRIMARY KEY,
  datecreated             timestamp NOT NULL,
  nickname                text UNIQUE,
  title                   text NOT NULL,
  description             text NOT NULL,
  owner                   integer NOT NULL,
  duplicateof             integer REFERENCES Bug,
  communityscore          integer NOT NULL,
  communitytimestamp      timestamp NOT NULL,
  activityscore           integer NOT NULL,
  activitytimestamp       timestamp NOT NULL,
  hits                    integer NOT NULL,
  hitstimestamp           timestamp NOT NULL
);



/*
  PersonBug_Relationship
  The relationship between a person and a bug.
*/
CREATE TABLE PersonBug_Relationship (
  person         integer NOT NULL REFERENCES Person,
  bug            integer NOT NULL REFERENCES Bug,
  label          integer NOT NULL REFERENCES Label
);



/*
  CodereleaseBug
  This is a bug status scorecard. It's not a global status for the
  bug, this is usually attached to a release, or a sourcepackage in
  a distro. So these tell you the status of a bug SOMEWHERE. The
  pointer to this tells you which bug, and on what thing (the 
  SOMEWHERE) the status is being described.
*/
CREATE TABLE CodereleaseBug (
  bug              integer NOT NULL REFERENCES Bug,
  coderelease      integer NOT NULL REFERENCES Coderelease,
  explicit         boolean NOT NULL,
  affected         integer NOT NULL REFERENCES Label,
  priority         integer NOT NULL REFERENCES Label,
  severity         integer NOT NULL REFERENCES Label,
  reportedby       integer NOT NULL REFERENCES Person,
  verifiedby       integer NOT NULL REFERENCES Person,
  lastmodifiedby   integer NOT NULL REFERENCES Person,
  PRIMARY KEY ( bug, coderelease )
);



/*
  SourcepackageBug
  The status of a bug with regard to a source package. This is different
  to the status on a specific release, because it includes the concept
  of workflow or prognosis ("what we intend to do with this bug") while
  the release bug status is static ("is the bug present or not").
*/
CREATE TABLE SourcepackageBug (
  bug                integer NOT NULL REFERENCES Bug,
  sourcepackage      integer NOT NULL REFERENCES Sourcepackage,
  bugstatus          integer NOT NULL REFERENCES Label,
  priority           integer NOT NULL REFERENCES Label,
  binarypackagename  text,
  PRIMARY KEY ( bug, sourcepackage )
);



/*
  Bug_Sourcepackage_Relationship
  This is a mapping of the relationship between a bug and a source
  package. Note that there is another similar table, the SourcepackageBug,
  that is dedicated to the status of a bug in a source package. This one is
  a bit more subtle. For example, you might put an intry in this table to
  indicate that a bug "victimises" a source package. In other words, the
  bug itself does not appear in this sourcepackage, but the functionality
  of the sourcepackage is somehow impacted by the bug.
*/
CREATE TABLE Bug_Sourcepackage_Relationship (
  bug                integer NOT NULL REFERENCES Bug,
  sourcepackage      integer NOT NULL REFERENCES Sourcepackage,
  label              integer NOT NULL REFERENCES Label
);



/*
  ProductBugStatus
  The status of a bug with regard to a product. This is different
  to the status on a specific release, because it includes the concept
  of workflow or prognosis ("what we intend to do with this bug") while
  the release bug status is static ("is the bug present or not").
*/
CREATE TABLE ProductBugStatus (
  bug                integer NOT NULL REFERENCES Bug,
  product            integer NOT NULL REFERENCES Sourcepackage,
  bugstatus          integer NOT NULL REFERENCES Label,
  priority           integer NOT NULL REFERENCES Label,
  PRIMARY KEY ( bug, product )
);



/*
  BugActivity
  A log of all the things that have happened to a bug, as Dave wants
  to keep track of it.
*/
CREATE TABLE BugActivity (
  bug           integer NOT NULL REFERENCES Bug,
  activitydate  timestamp NOT NULL,
  person        integer NOT NULL,
  whatchanged   text NOT NULL,
  oldvalue      text NOT NULL,
  newvalue      text NOT NULL,
  message       text NOT NULL
);
-- XXX this does not have a primary key, theory says it needs one!




/*
  BugExternalref
  A table of external references for a bug, that are NOT remote
  bug system references, except where the remote bug system is
  not supported by the BugWatch table.
 XXX can we set the default timestamp to "now"
*/
CREATE TABLE BugExternalref (
  bug         integer NOT NULL REFERENCES Bug,
  bugreftype  integer NOT NULL REFERENCES Label,
  data        text NOT NULL,
  description text NOT NULL,
  createdate  timestamp NOT NULL,
  owner       integer NOT NULL REFERENCES Person
);



/*
  BugSystemType
  This is a table of bug tracking system types. We don't have much
  version granularity (Bugzilla 2.15 is treated the same as Bugzilla 2.17
  unless you create them as two separate bug system types). This table is
  used by the BugSystem table to indicate the type of a remote bug system.
*/
CREATE TABLE BugSystemType (
  bugsystemtype   serial PRIMARY KEY,
  name            text NOT NULL UNIQUE,
  title           text NOT NULL,
  description     text NOT NULL,
  homepage        text,
  owner           integer NOT NULL REFERENCES Person -- who knows most about these
);
INSERT INTO BugSystemType VALUES ( 1, 'bugzilla', 'BugZilla', 'Dave Miller\'s Labour of Love, the Godfather of Open Source project issue tracking.', 'http://www.bugzilla.org/', 2 );
INSERT INTO BugSystemType VALUES ( 2, 'debbugs', 'DebBugs', 'The Debian bug tracking system, ugly as sin but fast and productive as a rabbit in high heels.', 'http://bugs.debian.org/', 3 );
INSERT INTO BugSystemType VALUES ( 3, 'roundup', 'Round-Up', 'Python-based open source bug tracking system with an elegant design and reputation for cleanliness and usability.', 'http://www.roundup.org/', 4 );


/*
  BugSystem
  A table of remote bug systems (for example, Debian's DebBugs, and
  Mozilla's Bugzilla, and SourceForge's tracker...). The baseurl is the
  top of the bug system's tree, from which the URL to a given bug
  status can be determined.
*/
CREATE TABLE BugSystem (
  bugsystem        serial PRIMARY KEY,
  bugsystemtype    integer NOT NULL REFERENCES BugSystemType,
  name             text NOT NULL,
  title            text NOT NULL,
  description      text NOT NULL,
  baseurl          text NOT NULL,
  owner            integer NOT NULL REFERENCES Person
);



/*
  BugWatch
  This is a table of bugs in remote bug systems (for example, upstream
  bugzilla's) which we want to monitor for status changes.
*/
CREATE TABLE BugWatch (
  bugwatch         serial PRIMARY KEY,
  bugsystem        integer NOT NULL REFERENCES BugSystem,
  remotebug        text NOT NULL, -- unique identifier of bug in that system
  remotestatus     text NOT NULL, -- textual representation of status
  lastchanged      timestamp NOT NULL,
  lastchecked      timestamp NOT NULL,
  owner            integer NOT NULL REFERENCES Person,
  datecreated      timestamp NOT NULL
);




/*
  ProjectBugsystem
  A link between the Project table and the Bugsystem table. This allows
  us to setup a bug system and then easily create watches once a bug
  has been assigned to an upstream product.
*/
CREATE TABLE ProjectBugsystem (
  project         integer NOT NULL REFERENCES Project,
  bugsystem       integer NOT NULL REFERENCES BugSystem,
  PRIMARY KEY ( project, bugsystem )
);
  


/*
  BugAttachment
  A table of attachments to bugs. These are typically patches, screenshots,
  mockups, or other documents.
*/
CREATE TABLE BugAttachment (
  bugattachment   serial PRIMARY KEY,
  bug             integer NOT NULL REFERENCES Bug,
  name            text NOT NULL,
  title           text NOT NULL,
  description     text NOT NULL
);



/*
  BugattachmentRevision
  The actual content of a bug attachment. There can be multiple
  uploads over time, each revision gets a changecomment.
*/
CREATE TABLE BugattachmentContent (
  bugattachment  integer NOT NULL REFERENCES BugAttachment,
  revisiondate   timestamp NOT NULL,
  changecomment  text NOT NULL,
  content        bytea NOT NULL,
  owner          integer REFERENCES Person,
  mimetype       text,
  PRIMARY KEY ( bugattachment, revisiondate )
);



/*
  BugLabel
  Allows us to attache arbitrary metadata to a bug.
*/
CREATE TABLE BugLabel (
  bug       integer NOT NULL REFERENCES Bug,
  label     integer NOT NULL REFERENCES Label,
  PRIMARY KEY ( bug, label )
);




/*
  Bug_Relationship
  The relationship between two bugs, with a label.
*/
CREATE TABLE Bug_Relationship (
  src        integer NOT NULL REFERENCES Bug,
  dst        integer NOT NULL REFERENCES Bug,
  label      integer NOT NULL REFERENCES Label
);




/*
  BugMessage
  A table of messages about bugs. Could be from the web
  forum, or from email, we don't care and treat them both
  equally. A message can apply to multiple forums.
*/
CREATE TABLE BugMessage (
  bugmessage           serial PRIMARY KEY,
  bug                  integer NOT NULL REFERENCES Bug,
  msgdate              timestamp NOT NULL,
  title                text NOT NULL, -- short title of comment
  contents             text NOT NULL, -- the message or full email with headers
  person               int REFERENCES Person, -- NULL if we don't know it
  parent               int REFERENCES BugMessage, -- gives us threading
  distribution         int REFERENCES Distribution,
  rfc822msgid          text
);




