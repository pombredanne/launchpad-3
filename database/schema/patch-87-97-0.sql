SET client_min_messages=ERROR;

-- Rename dateanswered column to reflect what it actually contains.
ALTER TABLE Question RENAME COLUMN dateanswered TO datesolved;
ALTER TABLE QuestionReopening RENAME COLUMN dateanswered TO datesolved;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 97, 0);
