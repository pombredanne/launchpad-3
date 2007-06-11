SET client_min_messages=ERROR;

/* Rosetta Firefox/OpenOffice.org updates
   Extension of Rosetta data model to allow native
   Firefox and OpenOffice import/export.
*/

-- Column which holds alternative message IDs for Firefox
ALTER TABLE potmsgset ADD COLUMN alternative_msgid TEXT;

-- Not needded due to unique constraint below
CREATE INDEX potmsgset_alternative_msgid_idx ON potmsgset(alternative_msgid);

ALTER TABLE POTMsgSet DROP CONSTRAINT potmsgset_potemplate_key;
CREATE UNIQUE INDEX potmsgset__potemplate__primemsgid__key
    ON POTMsgSet(potemplate, primemsgid)
    WHERE alternative_msgid IS NULL;
CREATE UNIQUE INDEX potmsgset__alternative_msgid__potemplate__key
    ON POTMsgSet(alternative_msgid, potemplate)
    WHERE alternative_msgid IS NOT NULL;

-- File format (defaults to PO) for translation imports
ALTER TABLE translationimportqueueentry
    ADD COLUMN format INTEGER DEFAULT 1 NOT NULL;

ALTER TABLE potemplate ADD COLUMN source_file INTEGER;
ALTER TABLE potemplate
    ADD COLUMN source_file_format INTEGER DEFAULT 1 NOT NULL;
ALTER TABLE POTemplate ADD CONSTRAINT potemplate__source_file__fk
    FOREIGN KEY (source_file) REFERENCES LibraryFileAlias;
CREATE INDEX potemplate__source_file__idx ON POTemplate(source_file)
    WHERE source_file IS NOT NULL;

-- Firefox special UUID
ALTER TABLE language
    ADD COLUMN uuid TEXT;
-- Firefox special UUID list
UPDATE language SET uuid='{95a05dab-bf44-4804-bb97-be2a3ee83acd}'
    WHERE code='af';
UPDATE language SET uuid='{b5cfaf65-895d-4d69-ba92-99438d6003e9}'
    WHERE code='ast';
UPDATE language SET uuid='{b5962da4-752e-416c-9934-f97724f07051}'
    WHERE code='bg';
UPDATE language SET uuid='{37b3f2ec-1229-4289-a6d9-e94d2948ae7e}'
    WHERE code='cs';
UPDATE language SET uuid='{1f391bb4-a820-4e44-8b68-01b385d13f94}'
    WHERE code='da';
UPDATE language SET uuid='{69C47786-9BEF-49BD-B99B-148C9264AF72}'
    WHERE code='de';
UPDATE language SET uuid='{6c3a4023-ca27-4847-a410-2fe8a2401654}'
    WHERE code='en';
UPDATE language SET uuid='{e4d01067-3443-405d-939d-a200ed3db577}'
    WHERE code='es';
UPDATE language SET uuid='{c5e1e759-ba2e-44b1-9915-51239d89c492}'
    WHERE code='fi';
UPDATE language SET uuid='{5102ddd3-a33f-436f-b43c-f9468a8f8b32}'
    WHERE code='fr';
UPDATE language SET uuid='{906b5382-9a34-4ab1-a627-39487b0678a9}'
    WHERE code='ga';
UPDATE language SET uuid='{16baab125756b023981bc4a14bd77b5c}'
    WHERE code='gu';
UPDATE language SET uuid='{9818f84c-1be1-4eea-aded-55f406c70e37}'
    WHERE code='he';
UPDATE language SET uuid='{cacb8e15-7f1b-4e71-a3c0-d63ce907366f}'
    WHERE code='hu';
UPDATE language SET uuid='{376b068c-4aff-4f66-bb4c-fde345b63073}'
    WHERE code='mk';
UPDATE language SET uuid='{83532d50-69a7-46d7-9873-ed232d5b246b}'
    WHERE code='nl';
UPDATE language SET uuid='{96f366b1-5194-4e30-9415-1f6fcaaaa583}'
    WHERE code='pa';
UPDATE language SET uuid='{cbfb6154-47f6-47ea-b888-6440a4ba44e8}'
    WHERE code='pl';
UPDATE language SET uuid='{8cb7341c-bcb6-43ca-b214-c48967f2a77e}'
    WHERE code='pt_BR';
UPDATE language SET uuid='{6e528a74-5cca-40d1-mozia152-d1b2d415210b}'
    WHERE code='pt';
UPDATE language SET uuid='{93ead120-1d61-4663-852d-ee631493168f}'
    WHERE code='ro';
UPDATE language SET uuid='{9E20245A-B2EE-4ee6-815B-99C30B35D0D2}'
    WHERE code='ru';
UPDATE language SET uuid='{ac25d192-0004-4228-8dc3-13a5461ca1c6}'
    WHERE code='sl';
UPDATE language SET uuid='{5ea95deb-8819-4960-837f-46de0f22bf81}'
    WHERE code='sq';
UPDATE language SET uuid='{A3E7CC55-B6E4-4a87-BD2E-657CA489F23A}'
    WHERE code='sv';
UPDATE language SET uuid='{08c0f953-0736-4989-b921-3e7ddfaf556a}'
    WHERE code='tr';
UPDATE language SET uuid='{74d253f5-1463-4de4-bc6e-a7127c066416}'
    WHERE code='zh_CN';
UPDATE language SET uuid='{0c7ce36c-a092-4a3d-9ac3-9891d2f2727e}'
    WHERE code='zh_TW';
UPDATE language SET uuid='{f3b38190-f8e0-4e8b-bf29-451fb95c0cbd}'
    WHERE code='ca';
UPDATE language SET uuid='{eb0c5e26-c8a7-4873-b633-0f453cb1debc}'
    WHERE code='el';
UPDATE language SET uuid='{9db167da-cba5-4d12-b045-5d2a5a36a88a}'
    WHERE code='it';
UPDATE language SET uuid='{02d61967-84bb-455b-a14b-76abc5864739}'
    WHERE code='ja';
UPDATE language SET uuid='{dcff4b08-a6cc-4588-a941-852609855803}'
    WHERE code='ko';
UPDATE language SET uuid='{4CD2763D-5532-4ddc-84D9-2E094695A680}'
    WHERE code='nb';
UPDATE language SET uuid='{f68df430-4534-4473-8ca4-d5de32268a8d}'
    WHERE code='uk';

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 7, 0);

