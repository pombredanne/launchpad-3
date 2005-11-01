SET client_min_messages=ERROR;

-- Drop all data from Branch and Revisions, and data dependent on that.

-- Remove everything, it's only sample data.
DELETE FROM ManifestEntry;
DELETE FROM ArchConfigEntry;

-- Remove everything. Will be repopulated.
DELETE FROM Changeset; 
DELETE FROM Branch;
DELETE FROM ArchUserId;

-- Branch Data Storage

ALTER TABLE Branch ADD COLUMN author integer
    CONSTRAINT branch_author_fk REFERENCES Person;

ALTER TABLE Branch ADD COLUMN name text;
ALTER TABLE Branch ADD CONSTRAINT valid_name CHECK (valid_branch_name(name));

ALTER TABLE Branch RENAME COLUMN description TO summary;

ALTER TABLE Branch ADD COLUMN branch_product_name text;

ALTER TABLE Branch ADD COLUMN product_locked boolean;

ALTER TABLE Branch ADD COLUMN home_page text;
ALTER TABLE Branch ADD CONSTRAINT valid_home_page
    CHECK (valid_absolute_url(home_page));

ALTER TABLE Branch ADD COLUMN branch_home_page text;
ALTER TABLE Branch ADD CONSTRAINT valid_branch_home_page
    CHECK (valid_absolute_url(branch_home_page));

ALTER TABLE Branch ADD COLUMN home_page_locked boolean;

ALTER TABLE Branch ADD COLUMN url text;
ALTER TABLE Branch ADD CONSTRAINT valid_url CHECK (valid_absolute_url(url));

ALTER TABLE Branch ADD COLUMN starred int;

ALTER TABLE Branch ADD COLUMN whiteboard text;

ALTER TABLE Branch ADD COLUMN lifecycle_status int;

ALTER TABLE Branch ADD COLUMN landing_target int
    CONSTRAINT branch_landing_target_fk REFERENCES Branch;

ALTER TABLE Branch ADD COLUMN current_delta_url text;
ALTER TABLE Branch ADD CONSTRAINT valid_current_delta_url
    CHECK (valid_absolute_url(current_delta_url));

ALTER TABLE Branch ADD COLUMN current_conflicts_url text;
ALTER TABLE Branch ADD CONSTRAINT valid_current_conflicts_url
    CHECK (valid_absolute_url(current_conflicts_url));

ALTER TABLE Branch ADD COLUMN current_diff_adds int;
ALTER TABLE Branch ADD COLUMN current_diff_deletes int;
ALTER TABLE Branch ADD COLUMN stats_updated timestamp without time zone;

ALTER TABLE Branch ADD COLUMN current_activity int;

ALTER TABLE Branch ADD COLUMN mirror_status int;

ALTER TABLE Branch ADD COLUMN last_mirrored timestamp without time zone;

ALTER TABLE Branch ADD COLUMN last_mirror_attempt timestamp without time zone;

ALTER TABLE Branch ADD COLUMN mirror_failures int;

ALTER TABLE Branch ADD COLUMN cache_url text;
ALTER TABLE Branch ADD CONSTRAINT valid_cache_url
    CHECK (valid_absolute_url(cache_url));

ALTER TABLE Branch ADD COLUMN started_at int;

-- NULLs and defaults for Branch
ALTER TABLE Branch ALTER COLUMN owner SET NOT NULL;
ALTER TABLE Branch ALTER COLUMN name SET NOT NULL;
ALTER TABLE Branch ALTER COLUMN product_locked SET DEFAULT false;
ALTER TABLE Branch ALTER COLUMN product_locked SET NOT NULL;
ALTER TABLE Branch ALTER COLUMN home_page_locked SET DEFAULT false;
ALTER TABLE Branch ALTER COLUMN starred SET DEFAULT 1;
ALTER TABLE Branch ALTER COLUMN starred SET NOT NULL;
ALTER TABLE Branch ALTER COLUMN lifecycle_status SET DEFAULT 1;
ALTER TABLE Branch ALTER COLUMN lifecycle_status SET NOT NULL;
ALTER TABLE Branch ALTER COLUMN current_activity SET DEFAULT 0;
ALTER TABLE Branch ALTER COLUMN current_activity SET NOT NULL;
ALTER TABLE Branch ALTER COLUMN mirror_status SET DEFAULT 1;
ALTER TABLE Branch ALTER COLUMN mirror_status SET NOT NULL;
ALTER TABLE Branch ALTER COLUMN mirror_failures SET DEFAULT 0;
ALTER TABLE Branch ALTER COLUMN mirror_failures SET NOT NULL;

-- BranchMessage

CREATE TABLE BranchMessage (
    id serial PRIMARY KEY,
    branch int NOT NULL CONSTRAINT branchmessage_branch_fk REFERENCES Branch,
    message int NOT NULL CONSTRAINT branchmessage_message_fk REFERENCES Message
    );

-- Revision (nee Changeset)

ALTER TABLE ManifestEntry DROP CONSTRAINT manifestentry_changeset_fk;
ALTER TABLE ArchConfigEntry DROP CONSTRAINT archconfigentry_changeset_fk;

ALTER TABLE Changeset RENAME TO Revision;
ALTER TABLE Changeset_id_seq RENAME TO revision_id_seq;


ALTER TABLE Revision ALTER COLUMN id SET DEFAULT
    nextval('public.revision_id_seq');

ALTER TABLE Revision ADD COLUMN owner int CONSTRAINT revision_owner_fk
    REFERENCES Person;
ALTER TABLE Revision ADD COLUMN revision_id text
    CONSTRAINT revision_revision_id_unique UNIQUE;
ALTER TABLE Revision RENAME COLUMN datecreated TO date_created;

-- NULLable? If not, what do we default it too?
ALTER TABLE Revision ADD COLUMN revision_date timestamp WITHOUT TIME ZONE;

ALTER TABLE Revision RENAME COLUMN logmessage TO log_body;
ALTER TABLE Revision RENAME COLUMN archid TO revision_author;
ALTER TABLE Revision ALTER COLUMN revision_author SET NOT NULL;
ALTER TABLE Revision ALTER COLUMN owner SET NOT NULL;
ALTER TABLE Revision ALTER COLUMN revision_id SET NOT NULL;

-- Drop unwanted columns
ALTER TABLE Revision DROP COLUMN branch;
ALTER TABLE Revision DROP COLUMN name;
ALTER TABLE Branch DROP COLUMN archnamespace;


ALTER TABLE ArchUserId RENAME TO RevisionAuthor;
ALTER TABLE archuserid_id_seq RENAME TO revisionauthor_id_seq;
ALTER TABLE RevisionAuthor ALTER COLUMN id
    SET DEFAULT nextval('revisionauthor_id_seq');
ALTER TABLE RevisionAuthor DROP COLUMN person;
ALTER TABLE RevisionAuthor RENAME COLUMN archuserid TO name;

CREATE TABLE RevisionParent (
    id serial PRIMARY KEY,
    sequence int NOT NULL,
    revision int NOT NULL CONSTRAINT revisionparent_revision_fk
        REFERENCES Revision,
    parent_id text NOT NULL
    );

ALTER TABLE RevisionParent ADD CONSTRAINT revisionparent_unique
    UNIQUE (revision, parent_id);

CREATE TABLE RevisionNumber (
    id serial PRIMARY KEY,
    sequence int NOT NULL,
    branch int NOT NULL CONSTRAINT revisionnumber_branch_fk
        REFERENCES Branch,
    revision int NOT NULL CONSTRAINT revisionnumber_revision_fk
        REFERENCES Revision
    );

ALTER TABLE RevisionNumber ADD CONSTRAINT revisionnumber_unique
    UNIQUE (sequence, branch, revision);

ALTER TABLE Branch ADD CONSTRAINT branch_started_at_fk
    FOREIGN KEY (started_at) REFERENCES RevisionNumber;

-- add constraint so branch.started_at.branch == branch

ALTER TABLE RevisionNumber ADD CONSTRAINT revisionnumber_branch_id_unique
    UNIQUE (branch, id);
ALTER TABLE Branch ADD CONSTRAINT branch_id_started_at_fk
    FOREIGN KEY (id, started_at) REFERENCES RevisionNumber (branch, id);

CREATE TABLE BranchSubscription (
    id serial PRIMARY KEY,
    person int NOT NULL
        CONSTRAINT branchsubscription_person_fk REFERENCES Person,
    branch int NOT NULL
        CONSTRAINT branchsubscription_branch_fk REFERENCES Branch
    );

-- Drop some obsolete tables
DROP TABLE ArchNamespace;
DROP TABLE ArchArchiveLocationSigner;
DROP TABLE ArchArchiveLocation;
DROP TABLE ArchArchive;
DROP TABLE ChangesetFileHash;
DROP TABLE ChangesetFile;
DROP TABLE ChangesetFilename;
DROP TABLE ProductBkBranch;

-- Tidy up some foreign keys
ALTER TABLE Branch DROP CONSTRAINT "$2";
ALTER TABLE Branch ADD CONSTRAINT branch_owner_fk FOREIGN KEY (owner)
    REFERENCES Person;
ALTER TABLE Branch DROP CONSTRAINT "$3";
ALTER TABLE Branch ADD CONSTRAINT branch_product_fk FOREIGN KEY (product)
    REFERENCES Product;

ALTER TABLE Revision DROP CONSTRAINT "$2";
ALTER TABLE Revision ADD CONSTRAINT revision_revision_author_fk
    FOREIGN KEY (revision_author) REFERENCES RevisionAuthor;
ALTER TABLE Revision DROP CONSTRAINT "$3";
ALTER TABLE Revision ADD CONSTRAINT revision_gpgkey_fk
    FOREIGN KEY (gpgkey) REFERENCES GPGKey;

-- Shazzham!
INSERT INTO LaunchpadDatabaseRevision VALUES (25, 99, 0);
