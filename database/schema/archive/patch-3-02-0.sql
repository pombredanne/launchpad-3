SET client_min_messages TO error;

/*
    Names not being constrained:
        ArchArchive.name
    
    Unsure:
        ArchConfig.name

        Builder.name

        ChangeSet.name

        Section.name

*/

ALTER TABLE BinaryPackageName ADD CONSTRAINT valid_name CHECK (valid_name(name));
ALTER TABLE BinaryPackageName DROP CONSTRAINT "$1";

ALTER TABLE Bug ADD CONSTRAINT valid_name CHECK (valid_name(name));
ALTER TABLE Bug DROP CONSTRAINT "$2";

ALTER TABLE BugAttachment ADD CONSTRAINT valid_name CHECK (valid_name(name));

ALTER TABLE BugTracker ADD CONSTRAINT valid_name CHECK (valid_name(name));
ALTER TABLE BugTracker DROP CONSTRAINT "$3";
ALTER TABLE BugTracker DROP CONSTRAINT "$4";

ALTER TABLE BugTrackerType ADD CONSTRAINT valid_name CHECK (valid_name(name));

/*
ALTER TABLE Builder ADD CONSTRAINT valid_name CHECK (valid_name(name));
*/

ALTER TABLE Component ADD CONSTRAINT valid_name CHECK (valid_name(name));

ALTER TABLE Distribution ADD CONSTRAINT valid_name CHECK (valid_name(name));
ALTER TABLE Distribution DROP CONSTRAINT "$2";

ALTER TABLE DistroRelease ADD CONSTRAINT valid_name CHECK (valid_name(name));
ALTER TABLE DistroRelease DROP CONSTRAINT "$6";

ALTER TABLE Label ADD CONSTRAINT valid_name CHECK (valid_name(name));

ALTER TABLE Person ADD CONSTRAINT valid_name CHECK (valid_name(name));
ALTER TABLE Person DROP CONSTRAINT "$2";

ALTER TABLE POTemplate ADD CONSTRAINT valid_name CHECK (valid_name(name));

ALTER TABLE Product ADD CONSTRAINT valid_name CHECK (valid_name(name));
ALTER TABLE Product DROP CONSTRAINT "$3";

ALTER TABLE ProductSeries ADD CONSTRAINT valid_name CHECK (valid_name(name));

ALTER TABLE Project ADD CONSTRAINT valid_name CHECK (valid_name(name));
ALTER TABLE Project DROP CONSTRAINT "$2";

ALTER TABLE Schema ADD CONSTRAINT valid_name CHECK (valid_name(name));
ALTER TABLE Schema DROP CONSTRAINT "$2";

ALTER TABLE SourcePackageName ADD CONSTRAINT valid_name 
    CHECK (valid_name(name));
ALTER TABLE SourcePackageName DROP CONSTRAINT lowercasename;

ALTER TABLE TranslationEffort ADD CONSTRAINT valid_name
    CHECK (valid_name(name));

