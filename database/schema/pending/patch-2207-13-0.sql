SET client_min_messages=ERROR;

ALTER TABLE CodeImport DROP CONSTRAINT valid_vcs_details;

ALTER TABLE CodeImport RENAME svn_branch_url TO url;

-- We seem to have leaked some whitespace. Fix it.
UPDATE CodeImport SET url = trim(url)
    WHERE url IS NOT NULL AND trim(url) <> url;

UPDATE CodeImport SET url = trim(git_repo_url) WHERE rcs_type = 4;

ALTER TABLE CodeImport DROP COLUMN git_repo_url;

DROP INDEX codeimport__svn_branch_url__idx;

ALTER TABLE CodeImport
    ADD CONSTRAINT codeimport__url__key UNIQUE (url),
    -- We may want to collapse the CVS details into the URL too at some
    -- point too.
    ADD CONSTRAINT valid_vcs_details CHECK (
        CASE
            WHEN rcs_type = 1 THEN
                cvs_root IS NOT NULL AND cvs_root <> ''
                AND cvs_module IS NOT NULL AND cvs_module <> ''
                AND url IS NULL
            ELSE
                cvs_root IS NULL AND cvs_module IS NULL
                AND url IS NOT NULL AND valid_absolute_url(url)
        END);

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 13, 0);

