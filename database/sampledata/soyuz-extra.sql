
-- Packaging
INSERT INTO Packaging (sourcepackage, packaging, product)
VALUES ((SELECT id FROM Sourcepackage WHERE id = 
	 (SELECT id from SourcepackageName WHERE name = 'mozilla-firefox')),
	1, -- dbschema.Packaging.PRIME
	(SELECT id FROM Product WHERE name = 'firefox'));
	
