SET client_min_messages=ERROR;

ALTER TABLE Karma ADD COLUMN product INTEGER REFERENCES Product(id);
ALTER TABLE Karma ADD COLUMN distribution INTEGER REFERENCES Distribution(id);
ALTER TABLE Karma ADD COLUMN sourcepackagename INTEGER REFERENCES SourcepackageName(id);

ALTER TABLE KarmaCache ADD COLUMN product INTEGER REFERENCES Product(id);
ALTER TABLE KarmaCache ADD COLUMN distribution INTEGER REFERENCES Distribution(id);
ALTER TABLE KarmaCache ADD COLUMN sourcepackagename INTEGER REFERENCES SourcepackageName(id);

SELECT person, sum(karmavalue) FROM KarmaCache 
WHERE person = 12
GROUP BY person
ORDER BY sum DESC;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 66, 0);

