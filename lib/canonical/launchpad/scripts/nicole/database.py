import re
from pyPgSQL import PgSQL
from string import split, join

# LaunchPad Dependencies
from canonical.foaf.nickname import generate_nick
from canonical.lp.encoding import guess as ensure_unicode

def data_sanitizer(data):    
    if not data:
        return data
    try:
        # check that this is unicode data
        data.decode("utf-8").encode("utf-8")
        return data
    except UnicodeError:
        # check that this is latin-1 data
        s = data.decode("latin-1").encode("utf-8")
        s.decode("utf-8")
        return s   
    #zope facility that doesn't work very well
    #return ensure_unicode(data)

class SQLThing:
    def __init__(self, dbname):
        self.dbname = dbname
        self.db = PgSQL.connect(database=self.dbname)

    def commit(self):
        return self.db.commit()
    
    def close(self):
        return self.db.close()

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

### XXX:cprov
# This class needs a lot of Love, it is fitting and cleaning data
# for the DB backend classes  
class FitData(object):
    pdisplayname = None
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

    def __init__(self, data, name):
        ## XXX cprov
        ## if no data is available
        ## Create an Empty Product
        if not data:
            self.name = name
            self.displayname = name
            self.title = name
            self.shortdesc = 'No Short Description Available'
            self.description = 'No Description Available'
            return
        
        ## XXX cprov
        ## both have devels        
        ## strange shit with wrong encode keys
        ## multiple devels and so
        try:
            self.pdisplayname = data_sanitizer(data['devels'].keys()[0])
            self.pemail = data_sanitizer(data['devels'].values()[0])
        except IndexError:
            print '@\tNo Devel'
            
        ## both have project
        self.name = data_sanitizer(data['product'])

        ## only SF has projectname
        if 'productaname' in data.keys():
            self.displayname = data_sanitizer(data['productname'])
            self.title = data_sanitizer(data['productname'])
        else:
            ## try to improve it
            self.displayname = data_sanitizer(data['product'])
            self.title = data_sanitizer(data['product'])

        ## both have shortdesc        
        if 'shortdesc' in data.keys():
            self.shortdesc = data_sanitizer(data['shortdesc'])
        else:
            self.shortdesc = data_sanitizer(data['description']).split(".")[0]

        ## both have description
        self.description = data_sanitizer(data['description'])

        ## both have homepage 
        self.homepage = data_sanitizer(data['homepage'])

        ## support several plangs
        try:
            plang_list = data['programminglang']
            temp_plang = ''
            for plang in plang_list:
                temp_plang += ' ' + plang  

            plang = data_sanitizer(temp_plang)
        except:
            plang = None

        screenshot = data_sanitizer(data['screenshot'])

        ## we cannot support several lists
        try:
            listurl = data_sanitizer(data['list'][0])
        except:
            listurl = None
    
        if 'sf' in data.keys():
            self.sourceforgeproject = data_sanitizer(data['sf'])
        else:
            self.sourceforgeproject = None

        if 'fm' in data.keys():
            self.freshmeatproject = data_sanitizer(data['fm'])
        else:
            self.freshmeatproject = None
 
 
class Doap(SQLThing):
    #
    # SourcePackageName
    #

    def getPackaging(self, product_id, package_id):
        return self._query_single("""SELECT * FROM Packaging
        WHERE product = %s AND sourcepackage = %s""",
                                  (product_id, package_id))

    def getSourcePackageByName(self, name):
        # only get the Ubuntu source package
        return self._query_single("""SELECT SourcePackage.id
            FROM SourcePackage,SourcePackagename
            WHERE SourcePackage.distro = 1 AND
            SourcePackage.sourcepackagename = SourcePackageName.id AND
            SourcePackageName.name = %s;""", (name,))

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
        name = data_sanitizer(name)

        #XXX: cprov
        # It shouldn't be here
        email = email.replace("__dash__", "")
        email = email.replace("|dash|", "")
        email = email.replace("[dash]", "")        
        email = email.replace(" ", "")
        
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

    def ensurePerson(self, displayname, email):
        person = self.getPersonByEmail(email)
        if person:
            return person
        # we will create a new person
        self.createPerson(displayname, email)
        return self.getPersonByEmail(email)

    def getProductByName(self, name):
        return self._query_single("""SELECT * FROM product WHERE name=%s;""",
                                  name)

    ##XXX: cprov
    ## Try to return the right project name (reviewed sf/fm one)
    ## not the DOAP name.
    def getProductsForUpdate(self):
        products = self._query("""SELECT name FROM product WHERE
                                  autoupdate=True AND reviewed=True;""")
        return len(products), [product[0] for product in products]

    def getProductSeries(self, product, name):
        return self._query_single("""SELECT * FROM productseries WHERE
        name=%s AND product=%s;""", (name, product))

    def updateProduct(self, data, productname, packagename):
        ## ensure packaging anyway
        if packagename:
            self.ensurePackaging(productname, packagename)

        ## if there is no data available simply return
        if not data:
            print '@\t No data available for Update'
            return
        
        fit = FitData(data, productname)

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
        self._update("product", dbdata, ("name='%s' and autoupdate=True"
                                         % productname))
        print '@\tUpdating ', productname        


    def createProduct(self, owner, fitted_data):

        fit = fitted_data
            
        datecreated = 'now()'

        ##XXX: (product+lastdoap) cprov 20041015
        ## Missed lastdoap field
        dbdata = {"owner":               owner,
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
        print '@\tProduct %s created' % fit.displayname

    def createProductRole(self, owner, product, role):
        dbdata = { "person":  owner,
                   "product": product,
                   "role": role,
                   }
        
        self._insert("productrole", dbdata)
        print '@\tProduct Role %s Created' % role

    def createProductSeries(self, product, name, displayname, shortdesc):
        dbdata = {"product":     product,
                  "name":        name,
                  "shortdesc":   shortdesc,
                  "displayname": displayname,
                  }
        
        self._insert("productseries", dbdata)
        print '@\tProduct Series %s Created' % displayname
            
    def ensureProduct(self, data, productname, packagename=None):

        if self.getProductByName(productname):
            self.updateProduct(data, productname, packagename)
            return 

        ## Fits the data (sanitizer, multiple entries handling, clean-up, etc)
        fit = FitData(data, productname)

        #XXX cprov 
        # Problems with wierd developers name and/or email
        try:
            owner = self.ensurePerson(fit.pdisplayname, fit.pemail)[0]
        except:
            print "@\t Mark wins a Product "
            owner = 1

        ## Create a product based on fitted data
        self.createProduct(owner, fit)

        ## Get the 'just inserted' product id
        product = self.getProductByName(fit.name)[0]
        ## XXX cprov
        ## Hardcoded Role too Member
        role = 1

        ## create productrole        
        self.createProductRole(owner, product, role)
        
        ## productseries

        ##XXX: (series+name) cprov 20041012
        ## Hardcoded Product Series Name as "head"
        name = 'head'
        ##XXX: (series+diaplyname) cprov 20041012
        ## Displayname composed by projectname-serie as
        ## apache-1.2 or Mozilla-head
        displayname = fit.displayname + ' Head'

        shortdesc = """This is the primary HEAD branch of the mainline
        revision control system for %s. Releases on this
        series are usually development milestones and test
        releases.""" % fit.displayname
        
        self.createProductSeries(product, name, displayname, shortdesc)
        
        ## product/source packaging
        if not packagename:
            return 

        self.ensurePackaging(productname, packagename) 


    def ensurePackaging(self, productname, packagename):
        
        product = self.getProductByName(productname)
        
        if product:
            product_id = product[0]
        else:
            ## Aborting !!!
            print '@ %s Product not Found !!!!' % productname
            return

        sourcepackage = self.getSourcePackageByName(packagename)
        
        if sourcepackage:
            package_id = sourcepackage[0]
        else:
            ## Aborting !!!
            print '@ %s SourcePackage not Found !!!!' % packagename
            return

        ## verify the respective packaging entry
        if self.getPackaging(product_id, package_id):
            print '@\tPackaging Entry Found'
            return
        
        ##XXX: hardcoded Prime Packaging
        packaging = 1

        dbdata = { "product" : product_id,
                   "sourcepackage": package_id,
                   "packaging": packaging,
                   }

        self._insert("packaging", dbdata)
        print '@\tPackaging %s - %s Created' % (productname, packagename)

        
