/*
AnswerContacts will have a flag to indicate if the person or team
want to recieve questions only in their preerred languages.
*/

SET client_min_messages=ERROR;

ALTER TABLE AnswerContact
    ADD COLUMN preferred_languages BOOLEAN DEFAULT False NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 97, 0);
