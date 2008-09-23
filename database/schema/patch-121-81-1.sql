SET client_min_messages=ERROR;

CREATE INDEX translationmessage__current_or_imported__idx ON translationmessage USING btree (potmsgset) WHERE ((is_current IS TRUE) OR (is_imported IS TRUE));

DROP INDEX translationmessage__83fix2__idx;

ANALYZE translationmessage;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 81, 1);
