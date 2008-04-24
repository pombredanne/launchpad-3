SET client_min_messages=ERROR;

-- Add columns
ALTER TABLE TranslationMessage
    ADD COLUMN potemplate integer REFERENCES POTemplate(id),
    ADD COLUMN language integer REFERENCES Language(id),
    ADD COLUMN variant text;

-- Create linking table
CREATE TABLE TranslationTemplateItem(
    id serial PRIMARY KEY,
    potemplate integer NOT NULL REFERENCES POTemplate(id),
    sequence integer NOT NULL CHECK (sequence > 0),
    potmsgset integer NOT NULL REFERENCES POTMsgSet(id));

CREATE UNIQUE INDEX translationtemplateitem__potemplate__potmsgset__key
ON TranslationTemplateItem(potemplate, potmsgset);

CREATE INDEX translationtemplateitem__potmsgset__idx
ON TranslationTemplateItem(potmsgset);


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 46, 0);
