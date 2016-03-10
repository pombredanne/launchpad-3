-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE archive
    ADD COLUMN signing_key_owner integer REFERENCES Person,
    ADD COLUMN signing_key_fingerprint text,
    ADD CONSTRAINT valid_signing_key_fingerprint CHECK (
        signing_key_fingerprint IS NULL
        OR valid_fingerprint(signing_key_fingerprint))
        NOT VALID;

ALTER TABLE packageupload
    ADD COLUMN signing_key_owner integer REFERENCES Person,
    ADD COLUMN signing_key_fingerprint text,
    ADD CONSTRAINT valid_signing_key_fingerprint CHECK (
        signing_key_fingerprint IS NULL
        OR valid_fingerprint(signing_key_fingerprint))
        NOT VALID;

ALTER TABLE revision
    ADD COLUMN signing_key_owner integer REFERENCES Person,
    ADD COLUMN signing_key_fingerprint text,
    ADD CONSTRAINT valid_signing_key_fingerprint CHECK (
        signing_key_fingerprint IS NULL
        OR valid_fingerprint(signing_key_fingerprint))
        NOT VALID;

-- Already has "owner".
ALTER TABLE signedcodeofconduct
    ADD COLUMN signing_key_fingerprint text,
    ADD CONSTRAINT valid_signing_key_fingerprint CHECK (
        signing_key_fingerprint IS NULL
        OR valid_fingerprint(signing_key_fingerprint))
        NOT VALID;

ALTER TABLE sourcepackagerelease
    ADD COLUMN signing_key_owner integer REFERENCES Person,
    ADD COLUMN signing_key_fingerprint text,
    ADD CONSTRAINT valid_signing_key_fingerprint CHECK (
        signing_key_fingerprint IS NULL
        OR valid_fingerprint(signing_key_fingerprint))
        NOT VALID;

-- Pre-validating the constraints is slow (full table scan), and
-- ALTER TABLE ... VALIDATE CONSTRAINT before 9.4 takes a very unpleasant
-- ACCESS EXCLUSIVE lock, so we seem to be stuck with minutes of downtime.
-- But we know that the columns are new and null, so the constraints are
-- definitely satisfied at this point. Manually hack them to validated.
UPDATE pg_constraint SET convalidated=true
FROM pg_class, pg_namespace
WHERE
    pg_class.oid = pg_constraint.conrelid
    AND pg_namespace.oid = pg_class.relnamespace
    AND pg_constraint.conname = 'valid_signing_key_fingerprint'
    AND pg_namespace.nspname = 'public'
    AND pg_class.relname IN (
        'archive', 'packageupload', 'revision', 'signedcodeofconduct',
        'sourcepackagerelease');

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 75, 0);
