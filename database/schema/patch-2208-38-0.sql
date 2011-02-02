SET client_min_messages=ERROR;

CREATE TABLE PersonSettings (
    person integer PRIMARY KEY REFERENCES Person ON DELETE CASCADE,
    verbose_bugnotifications boolean NOT NULL DEFAULT FALSE,
    selfgenerated_bugnotifications boolean NOT NULL DEFAULT TRUE);

INSERT INTO PersonSettings
SELECT id, verbose_bugnotifications FROM Person;

CREATE TRIGGER populate_settings_t
AFTER INSERT ON Person FOR EACH ROW
EXECUTE PROCEDURE populate_settings();

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 38, 0);
