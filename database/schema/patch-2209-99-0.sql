-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE archive
    ADD COLUMN signing_key_owner integer REFERENCES Person,
    ADD COLUMN signing_key_fingerprint text,
    ADD CONSTRAINT valid_signing_key_fingerprint
        CHECK (valid_fingerprint(signing_key_fingerprint));

ALTER TABLE packageupload
    ADD COLUMN signing_key_owner integer REFERENCES Person,
    ADD COLUMN signing_key_fingerprint text,
    ADD CONSTRAINT valid_signing_key_fingerprint
        CHECK (valid_fingerprint(signing_key_fingerprint));

ALTER TABLE revision
    ADD COLUMN signing_key_owner integer REFERENCES Person,
    ADD COLUMN signing_key_fingerprint text,
    ADD CONSTRAINT valid_signing_key_fingerprint
        CHECK (valid_fingerprint(signing_key_fingerprint));

ALTER TABLE sourcepackagerelease
    ADD COLUMN signing_key_owner integer REFERENCES Person,
    ADD COLUMN signing_key_fingerprint text,
    ADD CONSTRAINT valid_signing_key_fingerprint
        CHECK (valid_fingerprint(signing_key_fingerprint));

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 99, 0);
