SET client_min_messages=ERROR;

/* Drop huge unnecessary index */
DROP INDEX pomsgset_index_pofile;
DROP INDEX binarypackage_binarypackagename_key2;

/* Fix some foreign key names */
ALTER TABLE ArchArchive DROP CONSTRAINT "$1";
ALTER TABLE ArchArchive ADD CONSTRAINT archarchive_owner_fk
    FOREIGN KEY ("owner") REFERENCES Person;

ALTER TABLE ArchArchiveLocation DROP CONSTRAINT "$1";
ALTER TABLE ArchArchiveLocation ADD CONSTRAINT archarchivelocation_archive_fk
    FOREIGN KEY (archive) REFERENCES ArchArchive;

ALTER TABLE ArchArchiveLocationSigner DROP CONSTRAINT "$1";
ALTER TABLE ArchArchiveLocationSigner DROP CONSTRAINT "$2";
ALTER TABLE ArchArchiveLocationSigner
    ADD CONSTRAINT archarchivelocationsigner_archarchivelocation_fk
    FOREIGN KEY (archarchivelocation) REFERENCES ArchArchiveLocation;
ALTER TABLE ArchArchiveLocationSigner
    ADD CONSTRAINT archarchivelocationsigner_gpgkey_fk
    FOREIGN KEY (gpgkey) REFERENCES GPGKey;

ALTER TABLE ArchConfig DROP CONSTRAINT "$1";
ALTER TABLE ArchConfig DROP CONSTRAINT "$2";
ALTER TABLE ArchConfig ADD CONSTRAINT archconfig_productrelease_fk
    FOREIGN KEY (productrelease) REFERENCES ProductRelease;
ALTER TABLE ArchConfig ADD CONSTRAINT archconfig_owner_fk
    FOREIGN KEY ("owner") REFERENCES Person;

ALTER TABLE ArchConfigEntry DROP CONSTRAINT "$1";
ALTER TABLE ArchConfigEntry DROP CONSTRAINT "$2";
ALTER TABLE ArchConfigEntry DROP CONSTRAINT "$3";
ALTER TABLE ArchConfigEntry DROP CONSTRAINT "$4";
ALTER TABLE ArchConfigEntry ADD CONSTRAINT archconfigentry_archconfig_fk
    FOREIGN KEY (archconfig) REFERENCES ArchConfig;
ALTER TABLE ArchConfigEntry ADD CONSTRAINT archconfigentry_branch_fk
    FOREIGN KEY (branch) REFERENCES Branch;
ALTER TABLE ArchConfigEntry ADD CONSTRAINT archconfigentry_changeset_fk
    FOREIGN KEY (changeset, branch) REFERENCES ChangeSet(id, branch);

ALTER TABLE ArchNamespace DROP CONSTRAINT "$1";
ALTER TABLE ArchNamespace ADD CONSTRAINT archnamespace_archarchive_fk
    FOREIGN KEY (archarchive) REFERENCES ArchArchive;

ALTER TABLE ArchUserId DROP CONSTRAINT "$1";
ALTER TABLE ArchUserId ADD CONSTRAINT archuserid_person_fk
    FOREIGN KEY (person) REFERENCES Person;

ALTER TABLE BinaryPackage DROP CONSTRAINT "$2";
ALTER TABLE BinaryPackage DROP CONSTRAINT "$3";
ALTER TABLE BinaryPackage DROP CONSTRAINT "$4";
ALTER TABLE BinaryPackage DROP CONSTRAINT "$5";
ALTER TABLE BinaryPackage ADD CONSTRAINT binarypackage_binarypackagename_fk
    FOREIGN KEY (binarypackagename) REFERENCES BinaryPackageName;
ALTER TABLE BinaryPackage ADD CONSTRAINT binarypackage_build_fk
    FOREIGN KEY (build) REFERENCES Build;
ALTER TABLE BinaryPackage ADD CONSTRAINT binarypackage_component_fk
    FOREIGN KEY (component) REFERENCES Component;
ALTER TABLE BinaryPackage ADD CONSTRAINT binarypackage_section_fk
    FOREIGN KEY (section) REFERENCES Section;

ALTER TABLE BinaryPackageFile DROP CONSTRAINT "$1";
ALTER TABLE BinaryPackageFile DROP CONSTRAINT "$2";
ALTER TABLE BinaryPackageFile ADD CONSTRAINT binarypackagefile_binarypackage_fk
    FOREIGN KEY (binarypackage) REFERENCES BinaryPackage;
ALTER TABLE BinaryPackageFile ADD CONSTRAINT binarypackagefile_libraryfile_fk
    FOREIGN KEY (libraryfile) REFERENCES LibraryFileAlias;

ALTER TABLE Bounty DROP CONSTRAINT "$1";
ALTER TABLE Bounty DROP CONSTRAINT "$2";
ALTER TABLE Bounty DROP CONSTRAINT "$3";
ALTER TABLE Bounty ADD CONSTRAINT bounty_owner_fk 
    FOREIGN KEY ("owner") REFERENCES Person;
ALTER TABLE Bounty ADD CONSTRAINT bounty_reviewer_fk
    FOREIGN KEY (reviewer) REFERENCES Person;
ALTER TABLE Bounty ADD CONSTRAINT bounty_claimant_fk
    FOREIGN KEY (claimant) REFERENCES Person;

INSERT INTO LaunchpadDatabaseRevision VALUES (11,3,0);
