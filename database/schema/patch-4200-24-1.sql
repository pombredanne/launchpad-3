SET client_min_messages=ERROR;

ALTER TABLE CodeImport DROP CONSTRAINT valid_vcs_details;
ALTER TABLE CodeImport ADD CONSTRAINT "valid_vcs_details" CHECK (
CASE
    WHEN rcs_type = 1
         THEN cvs_root IS NOT NULL AND cvs_root <> ''::text AND cvs_module IS NOT NULL AND cvs_module <> ''::text
              AND branch_url IS NULL
    WHEN rcs_type IN (2, 3, 4, 5)
         THEN cvs_root IS NULL AND cvs_module IS NULL
              AND branch_url IS NOT NULL AND valid_absolute_url(branch_url)
    ELSE false
END);
INSERT INTO LaunchpadDatabaseRevision VALUES (4200, 24, 1);
