SET client_min_messages=ERROR;

/* Rosetta Firefox/OpenOffice.org updates
   Extension of Rosetta data model to allow native
   Firefox and OpenOffice import/export.
*/

  -- Column which holds alternative message IDs for Firefox
ALTER TABLE potmsgset
    ADD COLUMN alternative_msgid TEXT DEFAULT NULL;
UPDATE potmsgset SET alternative_msgid=NULL;

CREATE INDEX potmsgset_alternative_msgid_idx ON potmsgset USING btree (alternative_msgid);

ALTER TABLE ONLY potmsgset
    DROP CONSTRAINT potmsgset_potemplate_key;
ALTER TABLE ONLY potmsgset
    ADD CONSTRAINT potmsgset_potemplate_key UNIQUE (potemplate, primemsgid, alternative_msgid);

ALTER TABLE translationimportqueueentry
    ADD COLUMN format INTEGER DEFAULT 1 NOT NULL;

-- Set format for existing imports to PO
UPDATE translationimportqueueentry SET format=1;

ALTER TABLE potemplate
    ADD COLUMN source_file INTEGER;
ALTER TABLE potemplate
    ADD COLUMN source_file_format INTEGER DEFAULT 1 NOT NULL;

ALTER TABLE ONLY potemplate
    ADD CONSTRAINT "$1" FOREIGN KEY (source_file) REFERENCES libraryfilealias(id);

-- Firefox special UUID
ALTER TABLE language
    ADD COLUMN uuid TEXT;

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 99, 0);

