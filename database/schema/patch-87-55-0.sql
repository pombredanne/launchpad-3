-- Add message context to the fields

SET client_min_messages=ERROR;

ALTER TABLE POTMsgSet ADD COLUMN context text DEFAULT NULL;

DROP INDEX potmsgset__potemplate__primemsgid__key;

CREATE UNIQUE INDEX potmsgset__potemplate__context__primemsgid__key ON potmsgset USING btree (potemplate, context, primemsgid) WHERE context IS NOT NULL;

CREATE UNIQUE INDEX potmsgset__potemplate__no_context__primemsgid__key ON potmsgset USING btree (potemplate, primemsgid) where context IS NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 55, 0);

