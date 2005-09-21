
set client_min_messages=ERROR;

ALTER TABLE Person ADD COLUMN homepage_content text;
ALTER TABLE Person ADD COLUMN emblem integer;
ALTER TABLE Person ADD CONSTRAINT person_emblem_fk
                       FOREIGN KEY (emblem)
                       REFERENCES LibraryFileAlias(id);
ALTER TABLE Person ADD COLUMN hackergotchi integer;
ALTER TABLE Person ADD CONSTRAINT person_hackergotchi_fk
                       FOREIGN KEY (hackergotchi)
                       REFERENCES LibraryFileAlias(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (25,24,0);
