/*
   EXTRA SOYUZ SAMPLE DATA
   
   This requires the Malone sample data, which is why it's not part of the main
   Soyuz sample data.
*/

-- Packaging
INSERT INTO Packaging (sourcepackage, packaging, product)
VALUES ((SELECT id FROM Sourcepackage WHERE id = 
	 (SELECT id from SourcepackageName WHERE name = 'mozilla-firefox')),
	1, -- dbschema.Packaging.PRIME
	(SELECT id FROM Product WHERE name = 'firefox'));
	
