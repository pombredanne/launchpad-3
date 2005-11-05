set client_min_messages=ERROR;

/* add a column to note whether a GPG key has been validated for
 * encryption.  Since the registration process requires encryption, we
 * can set the value for all existing data to TRUE.
 */

ALTER TABLE GpgKey ADD COLUMN can_encrypt boolean;
UPDATE GpgKey SET can_encrypt = TRUE;
ALTER TABLE GpgKey ALTER COLUMN can_encrypt SET DEFAULT FALSE;
ALTER TABLE GpgKey ALTER COLUMN can_encrypt SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 90, 0);
