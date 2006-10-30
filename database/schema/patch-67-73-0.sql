SET client_min_messages=ERROR;

/* Rosetta Firefox/OpenOffice.org updates
   Extension of Rosetta data model to allow native
   Firefox and OpenOffice import/export.
*/

  -- Allow for recording if someone is essential to a spec discussions
ALTER TABLE potmsgset
    ADD COLUMN alternative_msgid TEXT DEFAULT NULL;
UPDATE potmsgset SET alternative_msgid=NULL;

CREATE INDEX potmsgset_alternative_msgid_idx ON potmsgset USING btree (alternative_msgid);

ALTER TABLE translationimportqueueentry
    ADD COLUMN format INTEGER DEFAULT 1 NOT NULL;

UPDATE translationimportqueueentry SET format=1;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 73, 0);

