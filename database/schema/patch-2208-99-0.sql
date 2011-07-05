-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

-- Make the existing primary key index think it is not the primary key.
UPDATE pg_index SET indisprimary = FALSE
WHERE pg_index.indexrelid = 'oauthnonce_pkey'::regclass;

UPDATE pg_constraint SET contype = 'u'
WHERE
    conrelid='oauthnonce'::regclass
    AND conname='oauthnonce_pkey';


-- Make an existing index think it is the primary key.
UPDATE pg_index SET indisprimary = TRUE
WHERE pg_index.indexrelid =
    'oauthnonce__access_token__request_timestamp__nonce__key'::regclass;

UPDATE pg_constraint SET contype='p'
WHERE
    conrelid='oauthnonce'::regclass
    AND conname='oauthnonce__access_token__request_timestamp__nonce__key';


ALTER TABLE OAuthNonce DROP COLUMN id;

-- Rename our new primary key index to the old name to keep Slony-I happy.
ALTER INDEX oauthnonce__access_token__request_timestamp__nonce__key RENAME TO oauthnonce_pkey;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);

