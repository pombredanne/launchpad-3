
SET client_min_messages=ERROR;

ALTER TABLE POTemplateName ADD translationdomain text;
UPDATE POTemplateName SET translationdomain=name;
ALTER TABLE POTemplateName ALTER COLUMN translationdomain SET NOT NULL;
ALTER TABLE POTemplateName ADD CONSTRAINT
    potemplate_translationdomain_key UNIQUE(translationdomain);

INSERT INTO LaunchpadDatabaseRevision VALUES (11, 10, 0);

