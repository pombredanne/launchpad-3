SET client_min_messages TO ERROR;

ALTER TABLE PoMsgID DROP CONSTRAINT pomsgid_msgid_key;
CREATE UNIQUE INDEX pomsgid_msgid_key ON POMsgID (sha1(msgid));

UPDATE LaunchpadDatabaseRevision SET major=6, minor=25, patch=0;

