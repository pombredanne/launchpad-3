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
        data = dict(data)
        for key in data:
            if data[key] is None:
                del data[key]
        keys = data.keys()
        query = "INSERT INTO %s (%s) VALUES (%s)" \
                 % (table, ",".join(keys), ",".join(["%s"] * len(keys)))
        try:
            self._exec(query, data.values())
        except:
            print "Bad things happened, data was %s" % data
            raise

    def _update(self, table, data, clause):
        fieldstring = ''
        for key, value in data.items():
            if value:
                value = value.replace("'", "")
                fieldstring += """ %s='%s',""" % (key, value)

        ## delete the last ','
        fieldstring = fieldstring[:-1]
 
        query = "UPDATE %s SET %s WHERE %s;" % (table, fieldstring, clause)
        try:
            self._exec(query)
            #print query
        except:
            raise Error, "Bad things happened, data was %s" % data

class FitData(SQLThing):
    pname = None
    pemail = None
    name = None
    displayname = None
    title = None
    shortdesc = None
    description = None
    homepage = None
    screenshot = None
    wiki = None
    listurl = None
    download = None
    sourceforgeproject = None
    freshmeatproject = None
    plang = None

    
    def __init__(self, data):
        ## both have devels        
        ## strange shit with wrong encode keys
        ## multiple devels and so
        try:
            ## XXX:(multiple+owner) cprov
            ## We don't support multiple owners, so, use the first
            self.pname = data['devels'].keys()[0]
            self.pemail = data['devels'].values()[0]
        except:
            print '@ Exception on Owner Field !!! '
            try:
                print '@\tDEBUG:', self.pname
                print '@\tDEBUG:', self.pemail
            except:
                print '@\tDEBUG: No Devel'
 
        ## both have project
        self.name = self.ensure_string_format(data['product'])

        ## only SF has projectname
        try:
            self.displayname = self.ensure_string_format(data['productname'])
            self.title = self.ensure_string_format(data['productname'])
        except:
            ## try to improve it
            self.displayname = self.ensure_string_format(data['product'])
            self.title = self.ensure_string_format(data['product'])

        ## both have shortdesc        
        try:
            self.shortdesc = self.ensure_string_format(data['shortdesc'])
        except:
            self.shortdesc = self.ensure_string_format(data['description']).split(".")[0]

        ## both have description
        self.description = self.ensure_string_format(data['description'])

        ## both have homepage 
        try:
            self.homepage = self.ensure_string_format(data['homepage'])
        except:
            self.homepage = None

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

        ## we cannot support several lists
        try:
            listurl = self.ensure_string_format(data['list'][0])
        except:
            listurl = None
    
        try:
            self.sourceforgeproject = self.ensure_string_format(data['sf'])
        except:
            self.sourceforgeproject = None

        try:
            self.freshmeatproject = self.ensure_string_format(data['fm'])
        except:
            self.freshmeatproject = None
 
 
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
        # only get the Ubuntu source package
        return self._query_single("""SELECT id FROM SourcePackage,
            SourcePackagename WHERE
            SourcePackage.distro = 1 AND
            SourcePackage.sourcepackagename = SourcePackageName.id AND
            SourcePackageName.name = %s);""", (name,))

    def getSourcePackageName(self, name):
        return self._query_single("""SELECT id FROM sourcepackagename
                                     WHERE name = %s;""", (name,))

    def getSourcePackageNames(self):
        return self._query_to_dict("""SELECT name FROM sourcepackagename;""")

    def getPersonByEmail(self, email):
        return self._query_single("""SELECT
            Person.id FROM Person,emailaddress 
            WHERE email = %s AND 
            Person.id = emailaddress.person;""", (email,))
 
    def getPersonByName(self, name):
        return self._query_single("""SELECT Person.id FROM Person
                                     WHERE name = %s""", (name,))

    def createPerson(self, name, email):
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
            "status":   1, # Status 'New' 
        }
        self._insert("emailaddress", data)

    def ensurePerson(self, name, email):
        person = self.getPersonByEmail(email)
        if person:
            return person
        # XXX this check isn't exactly right -- if there are name
        # collisions, we just add addresses because there is no way to
        # validate them. Bad bad kiko.
        person = self.getPersonByDisplayName(name)

        if person:
            print "@\tAdding address <%s> for %s" % (email, name)
            self.createEmail(people[0], email)
            return person

        self.createPeople(name, email)

        return self.getPersonByEmail(email)

    #
    # Project
    #
    def ensureProject(self, data):

        if self.getProject(data["project"]):
            print '@\tProject Already Included'
            return

        fit = FitData(data)

        owner = self.ensurePerson(fit.pname, fit.pemail)[0]

        datecreated = 'now()'
        
        ##XXX: (project+lastdoap) cprov 20041015
        ## Missing just lastdoap field
        dbdata = {"owner":               owner,
                  "name" :               fit.name,
                  "displayname":         fit.displayname,
                  "title" :              fit.title,
                  "shortdesc" :          fit.shortdesc,
                  "description":         fit.description,
                  "datecreated":         datecreated,
                  "homepageurl":         fit.homepage,
                  "wikiurl":             fit.wiki,
                  "sourceforgeproject":  fit.sourceforgeproject,
                  "freshmeatproject":    fit.freshmeatproject,
                  }
                                          
        self._insert("project", dbdata)
        print '@\tProject %s Created' % fit.displayname

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

    def getProjectByName(self, name):
        return self._query_single("""SELECT id FROM project WHERE name=%s;
        """, name)

    def getProductByName(self, name):
        return self._query_single("""SELECT * FROM product WHERE name=%s;""", name)

    def getProductsForUpdate(self):
        products = self._query("""SELECT * FROM product WHERE
        autoupdate=True AND reviewed=True;""")
        return len(products), products

    def getProductSeries(self, product, name):
        return self._query_single("""SELECT * FROM productseries WHERE
        name=%s AND product=%s;""", (name, product))

    def updateProduct(self, data, product_name):
        fit = FitData(data)

        # only update peripheral data, rather than the summary and
        # description, when we are in update mode.
        dbdata = {"homepageurl":         fit.homepage,
                  "screenshotsurl":      fit.screenshot,
                  "listurl":             fit.listurl,
                  "downloadurl":         fit.download,
                  "programminglang":     fit.plang,
                  "sourceforgeproject":  fit.sourceforgeproject,
                  "freshmeatproject":    fit.freshmeatproject,             
                }
                                          
        # the query reinforces the requirement that we only update when the
        # autoupdate field is true
        self._update("product", dbdata, ("name='%s' and autoupdate=True" % product_name))
        print '@\tProduct %s Updated' % fit.displayname

    def ensureProduct(self, project, data, source):

        project_result = self.getProject(project)

        if project_result:
            project_id = project_result[0]
            
        if self.getProduct(project_id, data['project']):
            print '@\tSkipping Already Added Project'        
            return 

        fit = FitData(data)

        owner = self.ensurePerson(fit.pname, fit.pemail)[0]
        datecreated = 'now()'

        ##XXX: (product+lastdoap) cprov 20041015
        ## Missed lastdoap field
        dbdata = {"project":             project_id,
                  "owner":               owner,
                  "name" :               fit.name,
                  "displayname":         fit.displayname,
                  "title":               fit.title,
                  "shortdesc":           fit.shortdesc,
                  "description":         fit.description,
                  "datecreated":         datecreated,
                  "homepageurl":         fit.homepage,
                  "screenshotsurl":      fit.screenshot,
                  "listurl":             fit.listurl,
                  "programminglang":     fit.plang,
                  "downloadurl":         fit.download,
                  "sourceforgeproject":  fit.sourceforgeproject,
                  "freshmeatproject":    fit.freshmeatproject,
                  }
                                          
        self._insert("product", dbdata)
        print '@\tProduct %s Created' % fit.displayname


        ## productrole
        product = self.getProduct(project_id, fit.name)[0]
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
        displayname = fit.displayname + '-' + name
        
        dbdata = {"product":     product,
                  "name":        name,
                  "shortdesc":   fit.shortdesc,
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

        ## isolate productseries id
        productseries = self.getProductSeries(product, displayname)[0]
        
        dbdata = {"product":       product,
                  "datereleased":  datereleased,
                  "version":       version,
                  "title":         fit.title,
                  "shortdesc":     fit.shortdesc,
                  "description":   fit.description,
                  "changelog":     changelog, 
                  "owner":         owner,
                  "productseries": productseries
                  }

        self._insert("productrelease", dbdata)
        print '@\tProduct Release %s Created' % fit.title


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

