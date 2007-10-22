SET client_min_messages=ERROR;

/*
   Add changelog to distributionsourcepackagecache so that changelogs on
   source packages can be searched.
*/

ALTER TABLE distributionsourcepackagecache ADD COLUMN changelog TEXT;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 10, 0);

