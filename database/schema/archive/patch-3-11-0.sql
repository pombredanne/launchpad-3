SET client_min_messages TO error;

CREATE TABLE PersonLanguage (
     id serial CONSTRAINT personlanguage_pkey PRIMARY KEY,
     person integer NOT NULL 
        CONSTRAINT personlanguage_person_fk REFERENCES Person(id),
     language integer NOT NULL 
        CONSTRAINT personlanguage_language_fk REFERENCES Language(id),
     CONSTRAINT personlanguage_person_key UNIQUE (person, language)
);

