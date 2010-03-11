SET client_min_messages=ERROR;
alter table sourcepackagerelease add changelog text;
INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);
