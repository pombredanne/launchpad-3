ALTER TABLE person ADD column language int;
ALTER TABLE person ADD CONSTRAINT person_language_fk FOREIGN KEY(language) REFERENCES language(id);
