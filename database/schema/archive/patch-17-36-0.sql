SET client_min_messages=ERROR;

DELETE FROM PersonLanguage WHERE language IN
(SELECT id FROM Language WHERE visible = False); 

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 36, 0);

