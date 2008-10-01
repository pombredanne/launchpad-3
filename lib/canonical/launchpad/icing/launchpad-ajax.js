// An AJAX client that runs against Launchpad's web service.

function LaunchpadClient() {}
LaunchpadClient.prototype = {
    'base': extract_webservice_start(location.href),
    'get': launchpad_get,
    'follow_created_redirect': launchpad_follow_created_redirect,
    'named_get' : launchpad_named_get,
    'named_post' : launchpad_named_post,
    'wrap_resource': launchpad_wrap_resource,
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
    deferred.addCallback(this.wrap_resource, this, uri);
    deferred.addCallback(callback);
    deferred.addErrback(errback);
}

function launchpad_named_get(uri, operation_name, parameters,
                             callback, errback, start, size) {
    final_uri = uri;
    if (uri.indexOf('?') == -1) {
        final_uri += '?'
    } else {
        final_uri += '&'
    }
    final_uri += "ws.op=" + operation_name;
    for (name in parameters) {
        final_uri += '&' + escape(name) + '=' + escape(parameters[name]);
    }
    if (start != undefined) {
        final_uri += '&ws.start=' + escape(start);
    }
    if (size != undefined) {
        final_uri += '&ws.size=' + escape(size);
    }

    return this.get(final_uri, callback, errback);
}

function launchpad_named_post(uri, operation_name, parameters,
                              callback, errback) {
    representation = "ws.op=" + operation_name;
    for (name in parameters) {
        representation += '&' + escape(name) + '=' + escape(parameters[name]);
    }
    deferred = doXHR(uri, {method: "POST",
                           sendContent: representation,
                           headers: {"Content-Type":
                                     "application/x-www-form-urlencoded"}});
    deferred.addCallback(this.follow_created_redirect);
    deferred.addCallback(this.wrap_resource, this, uri);
    deferred.addCallback(callback);
    deferred.addErrback(errback);
}

function launchpad_wrap_resource(client, uri, representation) {
    if (representation.resource_type_link == undefined) {
        // This is a non-entry object returned by a named operation.
        // It's either a list or a random JSON object.
        if (representation.total_size != undefined) {
            // It's a list. Treat it as a collection; it should be slicable.
            obj = new Collection(client, representation);
        }
        // It's a random JSON object. Leave it alone.
    } else if (representation.resource_type_link.search(/\/#service-root$/)
        != -1) {
        obj = new Launchpad(client, representation, uri);
    } else if (representation.total_size == undefined) {
        obj = new Entry(client, representation, uri);
    } else {
        obj = new Collection(client, representation, uri);
    }
    return succeed(obj);
}

function launchpad_follow_created_redirect(response) {
    if (response.status == 201) {
        // A new object was created as a result of the operation.
        // Get that object and wrap it instead.
        new_location = response.getResponseHeader("Location");
        deferred = loadJSONDoc(new_location);
        deferred.redirected_uri = new_location;
        return succeed(deferred);
    }
    return succeed(response);
}


// Resource objects.

function Resource() {}
Resource.prototype = {
    'init': init_resource,
    'named_get': resource_named_get,
    'named_post': resource_named_post,
}

function init_resource(client, representation, uri) {
    this.lp_client = client;
    this.lp_original_uri = uri;
    for (key in representation) { this[key] = representation[key]; }
}

function resource_named_get(operation_name, parameters, callback,
                   errback, start, size) {
    this.lp_client.named_get(this.lp_original_uri, operation_name, parameters,
                             callback, errback, start, size);
}

function resource_named_post(operation_name, parameters, callback, errback) {
    this.lp_client.named_post(this.lp_original_uri, operation_name,
                              parameters, callback, errback);
}


// The service root resource.
function Launchpad(client, representation, uri) {
    this.init(client, representation, uri);
}
Launchpad.prototype = new Resource;

// The entry resource.
function Entry(client, representation, uri) {
    this.init(client, representation, uri);
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
function Collection(client, representation, uri) {
    this.init(client, representation, uri);
}
Collection.prototype = new Resource;
