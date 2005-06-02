SET client_min_messages=ERROR;

/* Create the table for a TranslationGroup */

CREATE TABLE TranslationGroup (
    id                 serial PRIMARY KEY,
    name               text NOT NULL,
    title              text,
    summary            text,
    datecreated        timestamp without time zone
                       DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    owner              integer NOT NULL
);

ALTER TABLE TranslationGroup ADD CONSTRAINT translationgroup_owner_fk
    FOREIGN KEY (owner) REFERENCES Person(id);
ALTER TABLE TranslationGroup ADD CONSTRAINT translationgroup_name_key
    UNIQUE (name);

/* Create the table for a Translator */

CREATE TABLE Translator (
    id                 serial PRIMARY KEY,
    translationgroup   integer NOT NULL,
    language           integer NOT NULL,
    translator         integer NOT NULL,
    datecreated        timestamp without time zone NOT NULL 
                       DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
    );

ALTER TABLE Translator ADD CONSTRAINT translator_translationgroup_fk
    FOREIGN KEY (translationgroup) REFERENCES TranslationGroup(id);
ALTER TABLE Translator ADD CONSTRAINT translator_language_fk
    FOREIGN KEY (language) REFERENCES Language(id);
ALTER TABLE Translator ADD CONSTRAINT translator_person_fk
    FOREIGN KEY (translator) REFERENCES Person(id);
ALTER TABLE Translator ADD CONSTRAINT translation_translationgroup_key
    UNIQUE (translationgroup, language);

ALTER TABLE Distribution ADD COLUMN translationgroup integer;
ALTER TABLE Distribution ADD COLUMN translationpermission integer;
ALTER TABLE Distribution ALTER COLUMN translationpermission SET DEFAULT 1;
UPDATE Distribution SET translationpermission=1;
ALTER TABLE Distribution ALTER COLUMN translationpermission SET NOT NULL;
ALTER TABLE ONLY Distribution
    ADD CONSTRAINT distribution_translationgroup_fk
        FOREIGN KEY (translationgroup)
        REFERENCES TranslationGroup(id);

ALTER TABLE Project ADD COLUMN translationgroup integer;
ALTER TABLE Project ADD COLUMN translationpermission integer;
ALTER TABLE Project ALTER COLUMN translationpermission SET DEFAULT 1;
UPDATE Project SET translationpermission=1;
ALTER TABLE Project ALTER COLUMN translationpermission SET NOT NULL;
ALTER TABLE ONLY Project
    ADD CONSTRAINT project_translationgroup_fk
        FOREIGN KEY (translationgroup)
        REFERENCES TranslationGroup(id);

ALTER TABLE Product ADD COLUMN translationgroup integer;
ALTER TABLE Product ADD COLUMN translationpermission integer;
ALTER TABLE Product ALTER COLUMN translationpermission SET DEFAULT 1;
UPDATE Product SET translationpermission=1;
ALTER TABLE Product ALTER COLUMN translationpermission SET NOT NULL;
ALTER TABLE ONLY Product
    ADD CONSTRAINT product_translationgroup_fk
        FOREIGN KEY (translationgroup)
        REFERENCES TranslationGroup(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 11, 0);

