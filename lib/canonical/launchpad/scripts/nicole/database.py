import re
from pyPgSQL import PgSQL
from string import split, join

from nickname import generate_nick

class SQLThing:
    def __init__(self, dbname):
        self.dbname = dbname
        self.db = PgSQL.connect(database=self.dbname)

    def commit(self):
        return self.db.commit()
    
    def close(self):
        return self.db.close()

    def ensure_string_format(self, name):
        try:
            # check that this is unicode data
            name.decode("utf-8").encode("utf-8")
            return name
        except UnicodeError:
            # check that this is latin-1 data
            s = name.decode("latin-1").encode("utf-8")
            s.decode("utf-8")
            return s

    def _get_dicts(self, cursor):
        names = [x[0] for x in cursor.description]
        ret = []
        for item in cursor.fetchall():
            res = {}
            for i in range(len(names)):
                res[names[i]] = item[i]
            ret.append(res)
        return ret

    def _query_to_dict(self, query, args=None):
        cursor = self._exec(query, args)
        return self._get_dicts(cursor)
        
    def _query(self, query, args=None):
        #print repr(query), repr(args)
        cursor = self.db.cursor()
        cursor.execute(query, args or [])
        results = cursor.fetchall()
        return results
    
    def _query_single(self, query, args=None):
        q = self._query(query, args)
        if len(q) == 1:
            return q[0]
        elif not q:
            return None
        else:
            raise AssertionError, "%s killed us on %s %s" \
                % (len(q), query, args)

    def _exec(self, query, args=None):
        #print repr(query), repr(args)
        cursor = self.db.cursor()
        cursor.execute(query, args or [])
        return cursor

    def _insert(self, table, data):
        keys = data.keys()
        query = "INSERT INTO %s (%s) VALUES (%s)" \
                 % (table, ",".join(keys), ",".join(["%s"] * len(keys)))
        try:
            self._exec(query, data.values())
        except:
            print "Bad things happened, data was %s" % data
            raise

class Doap(SQLThing):
    #
    # SourcePackageName
    #
    def ensureSourcePackageName(self, name):
        if self.getSourcePackageName(name):
            return
        name = self.ensure_string_format(name)
        self._insert("sourcepackagename", {"name": name})


    def getSourcePackage(self, name):
        return self._query_single("""SELECT id FROM Sourcepackage WHERE
                                     sourcepackagename = (SELECT id from
                                     sourcepackagename WHERE name = %s);""",
                                  (name,))
    

    def getSourcePackageName(self, name):
        return self._query_single("""SELECT id FROM sourcepackagename
                                     WHERE name = %s;""", (name,))

    ## insert LIMIT if necessary ...
    def getSourcePackageNames(self):
        return self._query_to_dict("""SELECT name FROM sourcepackagename;""")


    #
    # People
    #
    def getPeople(self, name, email):        
        name = self.ensure_string_format(name)
        email = self.ensure_string_format(email)
        self.ensurePerson(name, email)
        return self.getPersonByEmail(email)

    def getPersonByEmail(self, email):
        return self._query_single("""SELECT Person.id FROM Person,emailaddress 
                                     WHERE email = %s AND 
                                           Person.id = emailaddress.person;""",
                                  (email,))
    
    def getPersonByName(self, name):
        return self._query_single("""SELECT Person.id FROM Person
                                     WHERE name = %s""", (name,))
    
    def getPersonByDisplayName(self, displayname):
        return self._query_single("""SELECT Person.id FROM Person 
                                     WHERE displayname = %s""", (displayname,))

    def createPeople(self, name, email):
        print "@\tCreating Person %s <%s>" % (name, email)
        name = self.ensure_string_format(name)

        items = name.split()
        if len(items) == 1:
            givenname = name
            familyname = ""
        else:
            givenname = items[0]
            familyname = " ".join(items[1:])

        data = {
            "displayname":  name,
            "givenname":    givenname,
            "familyname":   familyname,
            "name":         generate_nick(email, self.getPersonByName),
        }
        self._insert("person", data)
        pid = self._query_single("SELECT CURRVAL('person_id_seq')")[0]
        self.createEmail(pid, email)
        
    def createEmail(self, pid, email):
        data = {
            "email":    email,
            "person":   pid,
            "status":   1, # XXX
        }
        self._insert("emailaddress", data)

    def ensurePerson(self, name, email):
        people = self.getPersonByEmail(email)
        if people:
            return people
        # XXX this check isn't exactly right -- if there are name
        # collisions, we just add addresses because there is no way to
        # validate them. Bad bad kiko.
        people = self.getPersonByDisplayName(name)

        if people:
            print "@\tAdding address <%s> for %s" % (email, name)
            self.createEmail(people[0], email)
            return people

        self.createPeople(name, email)

        return self.getPersonByEmail(email)
    #
    # Project
    #
    def ensureProject(self, data):

        if self.getProject(data["project"]):
            print '@\tProject Already Included'
            return

        ## both have devels        
        ## strange shit with wrong encode keys
        ## multiple devels and so
        try:
            name = data['devels'].keys()[0]
            email = data['devels'][name]            
            name = self.ensure_string_format(name)
            email = self.ensure_string_format(email)

            ## XXX:(multiple+owner) cprov
            ## We don't support multiple owners, so, use the first
            name = name.split(',')[0]
            email = email.split(',')[0]            
            owner = self.ensurePerson(name, email)[0]
        except:
            print '@ Exception on Owner Field !!! '
	    try: 
		print '@\tDEBUG:', name
		print '@\tDEBUG:', email
	    except:
		print '@\tDEBUG: No Devel'

            ## in case of 
	    owner = 1
                
        ## both have project
        name = self.ensure_string_format(data['project'])

        ## only SF has projectname
        try:
            displayname = self.ensure_string_format(data['projectname'])
            title = self.ensure_string_format(data['projectname'])
        except:
            ## try to imporve it
            displayname = self.ensure_string_format(data['project'])
            title = self.ensure_string_format(data['project'])

        ## XXX:both don't have shortdesc        
        save_desc = self.ensure_string_format(data['description'])

        ## use the maximun of 72 char and 10 words
        ## shortdesc = join(split(save_desc[:72])[:10])

        ## Get just the first paragraph 
        shortdesc = save_desc.split('.')[0]

        ## both have description
        description = self.ensure_string_format(data['description'])

        ## datecreated should be now()
        datecreated = 'now()'

        ## both have homepage 
        try:
            homepage = self.ensure_string_format(data['homepage'])
        except:
            homepage = None
        
        ##XXX need improve
        dbdata = {"owner":        owner,
                  "name" :        name,
                  "displayname" : displayname,
                  "title" :       title,
                  "shortdesc" :   shortdesc,
                  "description":  description,
                  "datecreated":  datecreated,
                  "homepageurl":  homepage,
                  }
                                          
        self._insert("project", dbdata)
        print '@\tProject %s Created' % displayname

        ## projectrole
        project = self.getProject(data["project"])[0]
        ## wtf is it ? verify dbschema
        role = 2
        dbdata = {"person": owner,
                  "project": project,
                  "role": role,            
                  }
        
        self._insert("projectrole", dbdata)
        print '@\tProject Role %s Created' % role

    def getProject(self, name):
        return self._query_single("""SELECT id FROM project WHERE name=%s;""",
                                  (name,))


    def getProduct(self, project, name):
        return self._query_single("""SELECT * FROM product WHERE name=%s
        AND project=%s;""", (name, project))

    def ensureProduct(self, project, data, source):
        project_result = self.getProject(project)

        if project_result:
            project_id = project_result[0]
            
        if self.getProduct(project_id, data['project']):        
            print '@\tSkipping Already Added Project'        
            return 

        ## both have devels        
        try:
            name = data['devels'].keys()[0]
            email = data['devels'][name]           
            name = self.ensure_string_format(name)
            email = self.ensure_string_format(email)
            ## XXX:(multiple+owner) cprov
            ## We don't support multiple owners, so, use the first
            name = name.split(',')[0]
            email = email.split(',')[0]            
            owner = self.ensurePerson(name, email)[0]
        except:
            print '@\tException on Owner Field !!! '
            print '@\tDEBUG:', name
            print '@\tDEBUG:', email
            owner = 1

            
        ## both have project
        name = self.ensure_string_format(data['project'])

        ## only SF has projectname
        try:
            displayname = self.ensure_string_format(data['projectname'])
            title = self.ensure_string_format(data['projectname'])
        except:
            ## try to imporve it
            displayname = self.ensure_string_format(data['project'])
            title = self.ensure_string_format(data['project'])

        ## XXX:both don't have shortdesc
        ## use the maximun of 72 char and 10 words
        save_desc = self.ensure_string_format(data['description'])
        shortdesc = join(split(save_desc[:72])[:10])

        ## both have description
        description = self.ensure_string_format(data['description'])

        ## datecreated should be now()
        datecreated = 'now()'

        ## both have homepage 
        try:
            homepage = self.ensure_string_format(data['homepage'])
        except:
            homepage = None
            
        ## support several plangs
        try:
            plang_list = data['programminglang']
            temp_plang = ''
            for plang in plang_list:
                temp_plang += ' ' + plang  

            plang = self.ensure_string_format(temp_plang)
        except:
            plang = None
            
        try:
            screenshot = self.ensure_string_format(data['screenshot'])
        except:
            screenshot = None

        ## support several lists
        try:
            orig_list = data['list']
            temp_list = '' 
            for url in orig_list:
                temp_list += ' ' + url                
            listurl = self.ensure_string_format(temp_list)
        except:
            listurl = None
        
        ##XXX need improve
        dbdata = {"project":      project_id,
                "owner":        owner,
                "name" :        name,
                "displayname":  displayname,
                "title":        title,
                "shortdesc":    shortdesc,
                "description":  description,
                "datecreated":  datecreated,
                "homepageurl":  homepage,
                "screenshotsurl": screenshot,
                "listurl":       listurl,
                "programminglang": plang,
                }
                                          
        self._insert("product", dbdata)
        print '@\tProduct %s Created' % displayname


        ## productrole
        product = self.getProduct(project_id, name)[0]
        ##XXX:  Hardcoded Role too Member
        role = 2 

        dbdata = { "person":  owner,
                   "product": product,
                   "role": role,
                   }
        
        self._insert("productrole", dbdata)
        print '@\tProduct Role %s Created' % role

        ## productseries

        ##XXX: (series+name) cprov 20041012
        ## Hardcoded Product Series Name as "head"
        name = 'head'
        ##XXX: (series+diaplyname) cprov 20041012
        ## Displayname composed by projectname-serie as
        ## apache-1.2 or Mozilla-head
        displayname = displayname + '-' + name
        
        dbdata = {"product":     product,
                  "name":        name,
                  "shortdesc":   shortdesc,
                  "displayname": displayname,
                  }

        self._insert("productseries", dbdata)
        print '@\tProduct Series %s Created' % displayname

        ## productreleases
        ## XXX: (productrelease+version) cprov 20041013
        ## where does it comes from ?? using hardcoded
        version = '1.0'

        ## XXX: (productrelease+changelog) cprov 20041013
        ## How to compose the changelog field ?
        changelog = 'Created by Nicole Script'
        ## XXX:  (productrelease+datereleased) cprov 20041013
        ## Datereleased should be acquired from data, let's insert
        ## now as quick&dirty strategy
        datereleased = 'now()'
        
        dbdata = {"product":       product,
                  "datereleased":  datereleased,
                  "version":       version,
                  "title":         title,
                  "description":   description,
                  "changelog":     changelog, 
                  "owner":         owner,
                  }

        self._insert("productrelease", dbdata)
        print '@\tProduct Release %s Created' % title


        ## product/source packaging
        sourcepackage = self.getSourcePackage(source)

        if sourcepackage:
            sourcepackage = sourcepackage[0]
        else:
            ## Aborting !!!
            print('@ Current SourcePackage not Found !!!!')
            return
        ##XXX: hardcoded Prime Packaging
        packaging = 1

        dbdata = { "product" : product,
                   "sourcepackage": sourcepackage,
                   "packaging": packaging,
                   }

        self._insert("packaging", dbdata)
        print '@\tPackaging Created' 


        
        
