SET client_min_messages=ERROR;

ALTER TABLE Branch ADD COLUMN registrant integer
    CONSTRAINT branch_registrant_fk REFERENCES Person;

ALTER TABLE Branch ADD COLUMN name text;
ALTER TABLE Branch ADD CONSTRAINT valid_name CHECK (valid_name(name));

ALTER TABLE Branch RENAME COLUMN description TO summary;

ALTER TABLE Branch ADD COLUMN branch_product_name text;

ALTER TABLE Branch ADD COLUMN product_locked boolean;
ALTER TABLE Branch ALTER COLUMN product_locked SET DEFAULT false;

ALTER TABLE Branch ADD COLUMN home_page text;
ALTER TABLE Branch ADD CONSTRAINT valid_home_page
    CHECK (valid_absolute_url(home_page));

ALTER TABLE Branch ADD COLUMN branch_home_page text;
ALTER TABLE Branch ADD CONSTRAINT valid_branch_home_page
    CHECK (valid_absolute_url(branch_home_page));

ALTER TABLE Branch ADD COLUMN home_page_locked boolean;
ALTER TABLE Branch ALTER COLUMN home_page_locked SET DEFAULT false;

ALTER TABLE Branch ADD COLUMN url text;
ALTER TABLE Branch ADD CONSTRAINT valid_url CHECK (valid_absolute_url(url));

ALTER TABLE Branch ADD COLUMN starred int;
ALTER TABLE Branch ALTER COLUMN starred SET DEFAULT 1;

ALTER TABLE Branch ADD COLUMN whiteboard text;

ALTER TABLE Branch ADD COLUMN branch_status int;
ALTER TABLE Branch ALTER COLUMN branch_status SET DEFAULT 1;

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
ALTER TABLE Branch ALTER COLUMN current_activity SET DEFAULT 0;

ALTER TABLE Branch ADD COLUMN mirror_status int;
ALTER TABLE Branch ALTER COLUMN mirror_status SET DEFAULT 1;

ALTER TABLE Branch ADD COLUMN last_mirrored timestamp without time zone;

ALTER TABLE Branch ADD COLUMN last_mirror_attempt timestamp without time zone;

ALTER TABLE Branch ADD COLUMN mirror_failures int;
ALTER TABLE Branch ALTER COLUMN mirror_failures SET DEFAULT 0;

ALTER TABLE Branch ADD COLUMN cache_url text;
ALTER TABLE Branch ADD CONSTRAINT valid_cache_url
    CHECK (valid_absolute_url(cache_url));

-- Migrate data
UPDATE Branch SET
    product_locked = DEFAULT,
    home_page_locked = DEFAULT,
    starred = DEFAULT,
    branch_status = DEFAULT,
    current_activity = DEFAULT,
    mirror_status = DEFAULT,
    mirror_failures = DEFAULT;

UPDATE Branch SET
    url = 'http://bazaar.ubuntu.com/'
        || archarchive.name || '/' || archnamespace.category ||
        '--' || archnamespace.branch || '--' || archnamespace.version
    FROM ArchArchive, ArchNamespace
        WHERE Branch.archnamespace = ArchNamespace.id
            AND ArchNamespace.archarchive = ArchArchive.id;
    

-- Set final column constraints after data migration
ALTER TABLE Branch ALTER COLUMN owner SET NOT NULL;
ALTER TABLE Branch ALTER COLUMN product_locked SET NOT NULL;
ALTER TABLE Branch ALTER COLUMN home_page_locked SET NOT NULL;
ALTER TABLE Branch ALTER COLUMN starred SET NOT NULL;
ALTER TABLE Branch ALTER COLUMN branch_status SET NOT NULL;
ALTER TABLE Branch ALTER COLUMN current_activity SET NOT NULL;
ALTER TABLE Branch ALTER COLUMN mirror_status SET NOT NULL;
ALTER TABLE Branch ALTER COLUMN mirror_failures SET NOT NULL;
-- TODO: Should name be NULLable? If so, need to set default values
-- ALTER TABLE Branch ALTER COLUMN name SET NOT NULL;

-- BranchMessage

CREATE TABLE BranchMessage (
    id serial PRIMARY KEY,
    branch int NOT NULL CONSTRAINT branchmessage_branch_fk REFERENCES Branch,
    message int NOT NULL CONSTRAINT branchmessage_message_fk REFERENCES Message
    );

-- Revision (nee Changeset)

ALTER TABLE Changeset RENAME TO Revision;
ALTER TABLE Changeset_id_seq RENAME TO revision_id_seq;
ALTER TABLE Revision ALTER COLUMN id SET DEFAULT
    nextval('public.revision_id_seq');

ALTER TABLE Revision ADD COLUMN owner int CONSTRAINT revision_owner_fk
    REFERENCES Person;

ALTER TABLE Revision ADD COLUMN revision_id text;

ALTER TABLE Revision RENAME COLUMN datecreated TO date_created;

-- NULLable? If not, what do we default it too?
ALTER TABLE Revision ADD COLUMN revision_date timestamp WITHOUT TIME ZONE;

ALTER TABLE Revision ADD COLUMN diff_adds int;
ALTER TABLE Revision ADD COLUMN diff_deletes int;
ALTER TABLE Revision RENAME COLUMN logmessage TO log_body;

ALTER TABLE Revision RENAME COLUMN archid TO revision_author;


-- Fill in Revision.owner from archuserid.person
-- Unfortunately, this does nothing as the archuserid table is empty
UPDATE Revision SET owner=archuserid.person
    FROM archuserid WHERE archuserid.person = Revision.revision_author;
-- Fill in Revision.revision_id from
UPDATE Revision SET
    revision_id=archarchive.name || '/' || 
    archnamespace.category || '--' || 
    archnamespace.branch || '--' ||
    archnamespace.version || '--' || revision.name
    FROM Branch, ArchNamespace, ArchArchive
    WHERE Revision.branch = Branch.id
        AND Branch.archnamespace = ArchNamespace.id
        AND ArchNamespace.archarchive = ArchArchive.id;

-- TODO: Can't set this yet as owner is not filled
--ALTER TABLE Revision ALTER COLUMN owner SET NOT NULL;
ALTER TABLE Revision ALTER COLUMN revision_id SET NOT NULL;

-- Drop unwanted columns
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
    revision int NOT NULL CONSTRAINT revisionparent_revision_fk
        REFERENCES Revision,
    parent int NOT NULL CONSTRAINT revisionparent_parent_fk REFERENCES Revision,
    -- TODO: This might not be wanted, as per XXX in spec
    committed_against int 
            CONSTRAINT revisionparent_committed_against_fk REFERENCES Revision
    );

CREATE TABLE BranchSubscription (
    id serial PRIMARY KEY,
    person int NOT NULL
        CONSTRAINT branchsubscription_person_fk REFERENCES Person,
    branch int NOT NULL
        CONSTRAINT branchsubscription_branch_fk REFERENCES Branch,
    subscription int NOT NULL -- dbschema
    );


-- Tidy up some foreign keys
ALTER TABLE Branch DROP CONSTRAINT "$2";
ALTER TABLE Branch ADD CONSTRAINT branch_owner_fk FOREIGN KEY (owner)
    REFERENCES Person;
ALTER TABLE Branch DROP CONSTRAINT "$3";
ALTER TABLE Branch ADD CONSTRAINT branch_product_fk FOREIGN KEY (product)
    REFERENCES Product;

ALTER TABLE Revision DROP CONSTRAINT "$1";
ALTER TABLE Revision ADD CONSTRAINT revision_branch_fk
    FOREIGN KEY (branch) REFERENCES Branch; 
ALTER TABLE Revision DROP CONSTRAINT "$2";
ALTER TABLE Revision ADD CONSTRAINT revision_revision_author_fk
    FOREIGN KEY (revision_author) REFERENCES RevisionAuthor;
ALTER TABLE Revision DROP CONSTRAINT "$3";
ALTER TABLE Revision ADD CONSTRAINT revision_gpgkey_fk
    FOREIGN KEY (gpgkey) REFERENCES GPGKey;
