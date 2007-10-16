-- For bug-106984 (Add who-made-private and when-made-private fields to the Bug table)

SET client_min_messages=ERROR;

ALTER TABLE Bug ADD COLUMN date_made_private
    TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL;
ALTER TABLE Bug ADD COLUMN who_made_private INTEGER DEFAULT NULL;

CREATE INDEX bug__who_made_private__idx ON Bug(who_made_private)
    WHERE who_made_private IS NOT NULL;

ALTER TABLE Bug ADD CONSTRAINT bug__who_made_private__fk
    FOREIGN KEY (who_made_private) REFERENCES Person;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 12, 0);
