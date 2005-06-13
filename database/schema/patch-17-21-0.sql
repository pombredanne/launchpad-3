/* This patch should be rolled out together with the changes */

set client_min_messages=ERROR;

ALTER TABLE gpgkey DROP COLUMN pubkey;
ALTER TABLE logintoken ADD COLUMN fingerprint text;

ALTER TABLE gpgkey ADD CONSTRAINT valid_fingerprint
    CHECK (valid_fingerprint(fingerprint));
ALTER TABLE gpgkey ADD CONSTRAINT valid_keyid
    CHECK (valid_keyid(keyid));

ALTER TABLE logintoken ADD CONSTRAINT valid_fingerprint
    CHECK (fingerprint IS NULL OR valid_fingerprint(fingerprint));

INSERT INTO LaunchpadDatabaseRevision VALUES (17,21,0);
