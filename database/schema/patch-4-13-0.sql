-- Binary Package needs an arch-independance flag
 
ALTER TABLE BinaryPackage
    ADD COLUMN architecturespecific boolean;
    
-- Now we need to populate the column...

-- First; everything is arch specific
UPDATE BinaryPackage SET architecturespecific=true;

-- Next; find all binarypackage entries which are _all.deb
UPDATE BinaryPackage SET architecturespecific=false WHERE
	id IN (SELECT BinaryPackage.id 
		 FROM BinaryPackage,
		      BinaryPackageFile,
		      LibraryFileAlias
		WHERE BinaryPackageFile.binarypackage = BinaryPackage.id
		  AND BinaryPackageFile.libraryfile = LibraryFileAlias.id
		  AND LibraryFileAlias.filename LIKE '%_all.deb')
	;

-- Finally mark that column as "not null"
ALTER TABLE BinaryPackage
    ALTER COLUMN architecturespecific SET NOT NULL;

UPDATE launchpaddatabaserevision SET major=4, minor=13, patch=0;

