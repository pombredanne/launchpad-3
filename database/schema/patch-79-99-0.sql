SET client_min_messages=ERROR;

/* Rosetta Firefox/OpenOffice.org updates
   Extension of Rosetta data model to allow native
   Firefox and OpenOffice import/export.
*/

  -- Column which holds alternative message IDs for Firefox
ALTER TABLE potmsgset
    ADD COLUMN alternative_msgid TEXT DEFAULT NULL;

CREATE INDEX potmsgset_alternative_msgid_idx ON potmsgset USING btree (alternative_msgid);

ALTER TABLE POTMsgSet DROP CONSTRAINT potmsgset_potemplate_key;
CREATE UNIQUE INDEX potmsgset__potemplate__primemsgid__key
    ON POTMsgSet(potemplate, primemsgid)
    WHERE alternative_msgid IS NULL;
CREATE UNIQUE INDEX potmsgset__alternative_msgid__potemplate__key
    ON POTMsgSet(alternative_msgid, potemplate)
    WHERE alternative_msgid IS NOT NULL;


-- File format (defaults to PO) for translation imports
ALTER TABLE translationimportqueueentry
    ADD COLUMN format INTEGER DEFAULT 1 NOT NULL;

ALTER TABLE potemplate
    ADD COLUMN source_file INTEGER;
ALTER TABLE potemplate
    ADD COLUMN source_file_format INTEGER DEFAULT 1 NOT NULL;

ALTER TABLE POTemplate ADD CONSTRAINT potemplate__source_file__fk
    FOREIGN KEY (source_file) REFERENCES LibraryFileAlias;
CREATE INDEX potemplate__source_file__idx ON POTemplate(source_file)
    WHERE source_file IS NOT NULL;


-- Firefox special UUID
ALTER TABLE language
    ADD COLUMN uuid TEXT;

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 99, 0);

