SET client_min_messages=ERROR;

-- Link bugs to HWDB submissions

CREATE TABLE HWSubmissionBug (
    id SERIAL PRIMARY KEY,
    submission INTEGER REFERENCES HWSubmission(id) NOT NULL,
    bug INTEGER REFERENCES Bug(id) NOT NULL,
    CONSTRAINT hwsubmissionbug__submission__bug__key
        UNIQUE (submission, bug)
);

CREATE INDEX hwsubmissionbug__bug
    ON HWSubmissionBug(bug);

INSERT INTO LaunchpadDatabaseRevision VALUES (121,74, 0);
