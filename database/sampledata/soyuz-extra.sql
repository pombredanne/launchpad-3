
-- Packaging
INSERT INTO Packaging (sourcepackage, packaging, product)
VALUES ((SELECT id FROM SourcePackage WHERE id = 
	 (SELECT id from SourcePackageName WHERE name = 'mozilla-firefox')),
	1, -- dbschema.Packaging.PRIME
	(SELECT id FROM Product WHERE name = 'firefox'));
	
