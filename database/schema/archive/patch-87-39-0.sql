SET client_min_messages=ERROR;

-- Rename dateanswered column to reflect what it actually contains.
ALTER TABLE Question RENAME COLUMN dateanswered TO date_solved;
ALTER TABLE QuestionReopening RENAME COLUMN dateanswered TO date_solved;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 39, 0);
