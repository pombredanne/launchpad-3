SET client_min_messages=ERROR;


-- Add support for a legacy identifier.
ALTER TABLE Person ADD COLUMN old_openid_identifier text;

-- Migrate the exisiting "bad" OpenID Idenifiers to the new column.
UPDATE Person
SET old_openid_identifier = openid_identifier;

-- We are now free to switch Person.openid_identifier to the
-- new identifier.


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 97, 0);
