SET client_min_messages=ERROR;

CREATE TABLE CodeImport (
    id SERIAL PRIMARY KEY,
    branch integer REFERENCES Branch UNIQUE NOT NULL,
    date_created TIMESTAMP WITHOUT TIME ZONE
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    registrant integer REFERENCES Person NOT NULL,

    rcs_type integer NOT NULL,
    svn_branch_url text,
    cvs_root text,
    cvs_module text,

    review_status integer DEFAULT 1 NOT NULL,

    CONSTRAINT valid_vcs_details CHECK (CASE
        WHEN rcs_type = 1 THEN
            cvs_root IS NOT NULL
            AND cvs_root <> ''
            AND cvs_module IS NOT NULL
            AND cvs_module <> ''
            AND svn_branch_url IS NULL
        WHEN rcs_type = 2 THEN
            cvs_root IS NULL
            AND cvs_module IS NULL
            AND svn_branch_url IS NOT NULL
            AND valid_absolute_url(svn_branch_url)
        ELSE
            FALSE
        END)
    );

-- constraints
CREATE UNIQUE INDEX codeimport__cvs_root__cvs_module__key
    ON CodeImport(cvs_root, cvs_module)
    WHERE cvs_root IS NOT NULL;
CREATE UNIQUE INDEX codeimport__svn_branch_url__idx
    ON CodeImport(svn_branch_url) WHERE svn_branch_url IS NOT NULL;

-- Index needed for people merge to run well
CREATE INDEX codeimport__registrant__idx ON CodeImport(registrant);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 20, 0);

