SET client_min_messages TO error;

/* Rosetta changes for Carlos */

ALTER TABLE pomsgidsighting DROP CONSTRAINT pomsgidsighting_pomsgset_key;
ALTER TABLE label add constraint label_schema_key unique(schema, name);

