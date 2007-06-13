SET client_min_messages=ERROR;

ALTER TABLE Person ADD COLUMN openid_identifier text UNIQUE;

-- Give every existing user an openid_identifier
CREATE TRIGGER temp_t_set_openid_identifier BEFORE UPDATE ON Person
FOR EACH ROW EXECUTE PROCEDURE set_openid_identifier();
UPDATE Person SET openid_identifier=NULL;
DROP TRIGGER temp_t_set_openid_identifier ON Person;

-- Make the openid_identifier column required
ALTER TABLE Person ALTER COLUMN openid_identifier SET NOT NULL;

-- Add a trigger so the new column is always filled in on creation
CREATE TRIGGER set_openid_identifier_t BEFORE INSERT ON Person
FOR EACH ROW EXECUTE PROCEDURE set_openid_identifier();

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 15, 0);
