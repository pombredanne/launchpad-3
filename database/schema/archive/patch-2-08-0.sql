SET client_min_messages TO error;

ALTER TABLE SourcePackageBugAssignment DROP CONSTRAINT "$3";
ALTER TABLE SourcePackageBugAssignment 
    RENAME COLUMN binarypackage TO binarypackagename;
ALTER TABLE SourcePackageBugAssignment ADD FOREIGN KEY (binarypackagename)
    REFERENCES BinaryPackageName;

/* GPG Key id's aren't necessarily unique, but fingerprints are */

ALTER TABLE GPGKey DROP CONSTRAINT gpgkey_keyid_key;
ALTER TABLE GPGKey ADD CONSTRAINT gpg_fingerprint_key UNIQUE(fingerprint);

ALTER TABLE ProjectBugSystem RENAME TO ProjectBugTracker;
ALTER TABLE ProjectBugTracker RENAME COLUMN bugsystem TO bugtracker;

