// An AJAX client that runs against Launchpad's web service.

function LaunchpadClient() {}
LaunchpadClient.prototype = {
    'base': extract_webservice_start(location.href),
    'get': launchpad_get,
    'wrap_resource': wrap_resource,
}

function extract_webservice_start(url) {
    host_start = url.indexOf('//');
    host_end = url.indexOf('/', host_start+2);
    return url.substring(0, host_end+1) + 'api/beta/';
}

function launchpad_get(uri, callback, errback) {
    if (uri.indexOf("http") != 0)
    {
        uri = this.base + uri;
    }
    deferred = loadJSONDoc(uri);
    deferred.addCallback(this.wrap_resource, uri);
    deferred.addCallback(callback);
    deferred.addErrback(errback);
}

function wrap_resource(uri, representation) {
    if (representation['resource_type_link'].search(/\/#service-root$/)
        != -1) {
        obj = new Launchpad(this, representation);
    } else if (representation['total_size'] == undefined) {
        obj = new Entry(this, representation);
    } else {
	obj = new Collection(this, representation);
    }
    return succeed(obj);
}

// Resource objects.

function Resource() {}
Resource.prototype = {
    'init': init_resource,
}

function init_resource(client, representation) {
    this.lp_client = client;
    for (key in representation) { this[key] = representation[key] }
}

// The service root resource.
function Launchpad(client, representation) {
    this.init(client, representation);
}
Launchpad.prototype = new Resource;

// The entry resource.
function Entry(client, representation) {
    this.init(client, representation);
}
Entry.prototype = new Resource;

function save_entry(callback, errback)
{
    representation = {}
    for (key in this) {
        if (key.indexOf("lp_") != 0 ){
            representation[key] = this[key];
        }
    }
    deferred = doXHR(this.self_link,
                     {method: "PUT",
                      sendContent: JSON.stringify(representation),
                      headers: {"Content-Type": "application/json"}});
    deferred.addCallback(callback);
    deferred.addErrback(errback);
}
Entry.prototype.lp_save = save_entry;

// The collection resource.
function Collection(client, representation) {
    this.init(client, representation);
}
Collection.prototype = new Resource;
