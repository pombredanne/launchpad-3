-- Binary Package needs an arch-independance flag
 
ALTER TABLE BinaryPackage
    ADD COLUMN archspecific boolean;
    
-- Now we need to populate the column...

-- First; everything is arch specific
UPDATE BinaryPackage SET archspecific=true;

-- Next; find all binarypackage entries which are _all.deb
UPDATE BinaryPackage SET archspecific=false WHERE
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
    ALTER COLUMN archspecific SET NOT NULL;

-- Mmm comments
COMMENT ON COLUMN BinaryPackage.archspecific IS 'This field indicates whether or not a binarypackage is architecture-specific. If it is not specific to any given architecture then it can automatically be included in all the distroarchreleases which pertain.';
	
