-- For bug-106984 (Add who-made-private and when-made-private fields to the Bug table)
ALTER TABLE Bug ADD COLUMN date_made_private TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL;
ALTER TABLE Bug ADD COLUMN who_made_private INTEGER DEFAULT NULL;
ALTER TABLE Bug ADD FOREIGN KEY (who_made_private) REFERENCES Person;
INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 0);
