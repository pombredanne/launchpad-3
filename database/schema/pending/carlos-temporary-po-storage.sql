CREATE TABLE RawPOFile (
  id         serial  NOT NULL PRIMARY KEY,
  file       text    NOT NULL,
  potemplate integer NOT NULL REFERENCES POTemplate(id),
  language   integer REFERENCES Language(id),
  variant    text,
  person     integer REFERENCES Person(id),
  datesent   timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
  CHECK (((language IS NULL) AND (variant IS NULL)) OR (language IS NOT NULL))
  );

COMMENT ON TABLE RawPOFile IS 'This table is a temporary storage for the pofiles/potemplates uploaded into Rosetta from the web interface.';
