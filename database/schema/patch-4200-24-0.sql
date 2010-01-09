SET client_min_messages=ERROR;

ALTER TABLE CodeImport ADD COLUMN branch_url text;
UPDATE CodeImport SET branch_url = git_repo_url WHERE rcs_type = 4;
UPDATE CodeImport SET branch_url = svn_branch_url WHERE rcs_type IN (2, 3);
DROP INDEX codeimport__svn_branch_url__idx;
DROP INDEX codeimport__git_repo_url__idx;
ALTER TABLE CodeImport DROP CONSTRAINT valid_vcs_details;
ALTER TABLE CodeImport ADD CONSTRAINT "valid_vcs_details" CHECK (
CASE
    WHEN rcs_type = 1
         THEN cvs_root IS NOT NULL AND cvs_root <> ''::text AND cvs_module IS NOT NULL AND cvs_module <> ''::text
              AND branch_url IS NULL
    WHEN rcs_type IN (2, 3, 4)
         THEN cvs_root IS NULL AND cvs_module IS NULL
              AND branch_url IS NOT NULL AND valid_absolute_url(branch_url)
    ELSE false
END);
ALTER TABLE CodeImport DROP COLUMN git_repo_url;
ALTER TABLE CodeImport DROP COLUMN svn_branch_url;

CREATE UNIQUE INDEX codeimport__branch_url__idx ON CodeImport USING btree (branch_url) WHERE (branch_url is NOT NULL);

INSERT INTO LaunchpadDatabaseRevision VALUES (4200, 24, 0);
