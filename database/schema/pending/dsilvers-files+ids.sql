/*
 * The linkage tables between sourcepackagerelease and the librarian
 * and also binarypackage and the librarian needs ids for sqlobject
 */

-- SourcePackageReleaseFile

ALTER TABLE SourcePackageReleaseFile
    ADD COLUMN id integer;

CREATE SEQUENCE sourcepackagereleasefile_id_seq;

ALTER TABLE SourcePackageReleaseFile
    ALTER COLUMN id SET DEFAULT nextval('sourcepackagereleasefile_id_seq');

ALTER TABLE SourcePackageReleaseFile
    ALTER COLUMN id SET NOT NULL;

ALTER TABLE SourcePackageReleaseFile
    ADD PRIMARY KEY (id);

-- BinaryPackageFile

ALTER TABLE BinaryPackageFile
    ADD COLUMN id integer;

CREATE SEQUENCE binarypackagefile_id_seq;

ALTER TABLE BinaryPackageFile
    ALTER COLUMN id SET DEFAULT nextval('binarypackagefile_id_seq');

ALTER TABLE BinaryPackageFile
    ALTER COLUMN id SET NOT NULL;

ALTER TABLE BinaryPackageFile
    ADD PRIMARY KEY (id);
