-- Clean up unused columns in Bug table.
ALTER TABLE Bug DROP hits;
ALTER TABLE Bug DROP hitstimestamp;
ALTER TABLE Bug DROP activityscore;
ALTER TABLE Bug DROP activitytimestamp;
ALTER TABLE Bug DROP communityscore;
ALTER TABLE Bug DROP communitytimestamp;

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 03, 0);
