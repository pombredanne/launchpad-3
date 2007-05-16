/*
AnswerContacts will have a flag to indicate if the person or team
want to recieve questions only in their preerred languages.
*/

SET client_min_messages=ERROR;

ALTER TABLE AnswerContact
    ADD COLUMN want_english BOOLEAN DEFAULT True NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 05, 0);
