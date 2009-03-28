SET client_min_messages=ERROR;

UPDATE Revision SET revision_date=date_created
WHERE revision_date > date_created;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 44, 0);
