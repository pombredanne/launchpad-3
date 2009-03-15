SET client_min_messages=ERROR;

ALTER TABLE CodeImport ADD COLUMN git_repo_url text;
ALTER TABLE CodeImport DROP CONSTRAINT valid_vcs_details;
ALTER TABLE CodeImport ADD CONSTRAINT "valid_vcs_details" CHECK (
CASE
    WHEN rcs_type = 1
         THEN cvs_root IS NOT NULL AND cvs_root <> ''::text AND cvs_module IS NOT NULL AND cvs_module <> ''::text
              AND svn_branch_url IS NULL
              AND git_repo_url IS NULL
    WHEN rcs_type = 2 OR rcs_type = 3
         THEN cvs_root IS NULL AND cvs_module IS NULL
              AND svn_branch_url IS NOT NULL AND valid_absolute_url(svn_branch_url)
              AND git_repo_url IS NULL
    WHEN rcs_type = 4
         THEN cvs_root IS NULL AND cvs_module IS NULL
              AND svn_branch_url IS NULL
              AND git_repo_url IS NOT NULL
    ELSE false
END);

CREATE UNIQUE INDEX codeimport__git_repo_url__idx ON CodeImport USING btree (git_repo_url) WHERE (git_repo_url is NOT NULL);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 38, 0);
