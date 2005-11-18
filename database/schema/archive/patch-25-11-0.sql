SET client_min_messages=ERROR;

-- Drop some pointless owners
ALTER TABLE Processor DROP COLUMN owner;
ALTER TABLE ProcessorFamily DROP COLUMN owner;

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 11, 0);

