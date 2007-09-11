SET client_min_messages=ERROR;

-- Submissions for the hardware database.

CREATE TABLE HWSystemFingerprint (
    id serial PRIMARY KEY,
    -- An identifier for a system. 
    fingerprint text NOT NULL
        CONSTRAINT hwsystemfingerprint__fingerprint__key UNIQUE
);

CREATE TABLE HWSubmission (
    id serial PRIMARY KEY,

    -- See doc/hwdb.txt for details about the columns.

    date_created timestamp NOT NULL,

    date_submitted timestamp NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),

    format integer NOT NULL,

    status integer NOT NULL DEFAULT 1,

    private boolean NOT NULL,

    contactable boolean NOT NULL,

    live_cd boolean NOT NULL DEFAULT false,

    submission_id text
        CONSTRAINT hwsubmission__submission_id__key UNIQUE NOT NULL,

    owner integer NOT NULL
        CONSTRAINT hwsubmission__owned__fk
        REFERENCES Person(id),

    distroarchseries integer
        CONSTRAINT hwsubmission__distroarchseries__fk
        REFERENCES DistroArchRelease(id),

    raw_submission integer NOT NULL
        CONSTRAINT hwsubmission__raw_submission__fk
        REFERENCES LibraryFileAlias(id),

    system_fingerprint integer NOT NULL
        CONSTRAINT hwsubmission__system_fingerprint__fk
        REFERENCES HWSystemFingerprint(id)
);

CREATE INDEX hwsubmission__status__idx ON HWSubmission(status);
CREATE INDEX hwsubmission__owner__idx ON HWSubmission(owner);
CREATE INDEX hwsubmission__raw_submission__idx 
    ON HWSubmission(raw_submission);
CREATE INDEX hwsubmission__system_fingerprint__idx
    ON HWSubmission(system_fingerprint);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 46, 0);
