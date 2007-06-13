DELETE FROM posubmission WHERE id IN (
    SELECT posubmission.id
        FROM posubmission,
	     pomsgset,
	     potmsgset,
	     pomsgid
	WHERE
	    posubmission.pomsgset=pomsgset.id AND 
	    potmsgset=potmsgset.id AND
	    primemsgid=pomsgid.id AND
	    published IS NOT TRUE AND
	    (msgid='translation-credits' OR
	     msgid='translator-credits' OR
	     msgid='translator_credits' OR
	     msgid=E'_:EMAIL OF TRANSLATORS\nYour emails' OR
	     msgid=E'_:NAME OF TRANSLATORS\nYour names'));
