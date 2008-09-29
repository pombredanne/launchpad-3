SET client_min_messages=ERROR;

DROP INDEX potmsgset__potemplate__context__primemsgid__key;
DROP INDEX potmsgset__potemplate__no_context__primemsgid__key;

CREATE UNIQUE INDEX potmsgset__potemplate__context__msgid_singular__msgid_plural__key ON potmsgset USING btree (potemplate, context, msgid_singular, msgid_plural) WHERE (context IS NOT NULL AND msgid_plural IS NOT NULL);

CREATE UNIQUE INDEX potmsgset__potemplate__context__msgid_singular__no_msgid_plural__key ON potmsgset USING btree (potemplate, context, msgid_singular) WHERE (context IS NOT NULL AND msgid_plural IS NULL);

CREATE UNIQUE INDEX potmsgset__potemplate__no_context__msgid_singular__msgid_plural__key ON potmsgset USING btree (potemplate, msgid_singular, msgid_plural) WHERE (context IS NULL AND msgid_plural IS NOT NULL);

CREATE UNIQUE INDEX potmsgset__potemplate__no_context__msgid_singular__no_msgid_plural__key ON potmsgset USING btree (potemplate, msgid_singular) WHERE (context IS NULL AND msgid_plural IS NULL);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 56, 0);
