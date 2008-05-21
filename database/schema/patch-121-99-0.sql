SET client_min_messages=ERROR;

DROP INDEX potmsgset__potemplate__context__primemsgid__key;
DROP INDEX potmsgset__potemplate__no_context__primemsgid__key;

-- XXX (Danilo, 2008-05-21): should we split these indexes into two each
-- by `msgid_plural IS NULL` as well?
CREATE UNIQUE INDEX potmsgset__potemplate__context__msgid_singular__msgid_plural__key ON potmsgset USING btree (potemplate, context, msgid_singular, msgid_plural) WHERE (context IS NOT NULL);

CREATE UNIQUE INDEX potmsgset__potemplate__no_context__msgid_singular__msgid_plural__key ON potmsgset USING btree (potemplate, msgid_singular, msgid_plural) WHERE (context IS NULL);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
