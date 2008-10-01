// An AJAX client that runs against Launchpad's web service.

// Generally useful functions.

var HTTP_CREATED = 201;

function append_start_and_size(uri, start, size) {
    //Append values for ws.start and ws.size to the given URI.
    return append_qs(uri,
                     queryString(['ws.start', 'ws.size'], [start, size]));
}

function append_qs_key_value(uri, key, value) {
    //Append a key-value pair to the given URI's query string.
    return append_qs(uri, queryString([[key], [value]]));
}

function append_qs(uri, value) {
    //Append to the given URI's query string.
    if (uri.indexOf('?') == -1) {
        uri += '?';
    } else {
        uri += '&';
    }
    return uri + value;
}

function extract_webservice_start(url) {
    // Extract the service's root URI from any Launchpad web service URI.
    var host_start = url.indexOf('//');
    var host_end = url.indexOf('/', host_start+2);
    return url.substring(0, host_end+1) + 'api/beta/';
}

// Set the location of an object found by following an HTTP redirect.
function set_redirect_location(location, representation) {
    representation.lp_redirect_location = location;
    return succeed(representation);
}


// The Launchpad client itself.

function LaunchpadClient() {}
LaunchpadClient.prototype = {
    'base': extract_webservice_start(location.href),
    'get': launchpad_get,
    'follow_created_redirect': launchpad_follow_created_redirect,
    'named_get' : launchpad_named_get,
    'named_post' : launchpad_named_post,
    'wrap_resource': launchpad_wrap_resource,
}

function launchpad_get(uri, start, size) {
    if (uri.indexOf("http") != 0) {
        uri = this.base + uri;
    }
    if (start != undefined) {
        uri = append_start_and_size(uri, start, size);
    }
    var deferred = loadJSONDoc(uri);
    deferred.addCallback(this.wrap_resource, this, uri);
    return deferred;
}

function launchpad_named_get(uri, operation_name, parameters,
                             start, size) {
    uri = append_qs_key_value(uri, "ws.op", operation_name);
    for (name in parameters) {
        uri = append_qs_key_value(uri, name, parameters[name]);
    }
    uri = append_start_and_size(uri, start, size);
    return this.get(uri);
}

function launchpad_named_post(uri, operation_name, parameters) {
    if (uri.indexOf("http") != 0) {
        uri = this.base + uri;
    }
    var representation = "ws.op=" + operation_name;
    for (name in parameters) {
        representation += '&' + escape(name) + '=' + escape(parameters[name]);
    }
    var deferred = doXHR(uri, {method: "POST",
                               sendContent: representation,
                               headers: {"Content-Type":
                                         "application/x-www-form-urlencoded"}});
    deferred.addCallback(this.follow_created_redirect);
    deferred.addCallback(this.wrap_resource, this, uri);
    return deferred;
}

function launchpad_follow_created_redirect(response) {
    if (response.status == HTTP_CREATED) {
        // A new object was created as a result of the operation.
        // Get that object and wrap it instead.
        var new_location = response.getResponseHeader("Location");
        var deferred = loadJSONDoc(new_location);
        deferred.addCallback(set_redirect_location, new_location);
        return deferred;
    }
    return succeed(response);
}

function launchpad_wrap_resource(client, uri, representation) {
    var obj = undefined;
    if (representation.lp_redirect_location != undefined) {
        uri = representation.lp_redirect_location;
    }
    if (representation.resource_type_link == undefined) {
        // This is a non-entry object returned by a named operation.
        // It's either a list or a random JSON object.
        if (representation.total_size != undefined) {
            // It's a list. Treat it as a collection; it should be slicable.
            obj = new Collection(client, representation, uri);
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

function resource_named_get(operation_name, parameters, start, size) {
    return this.lp_client.named_get(this.lp_original_uri, operation_name,
                                    parameters, start, size);
}

function resource_named_post(operation_name, parameters) {
    return this.lp_client.named_post(this.lp_original_uri, operation_name,
                                     parameters);
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

function save_entry()
{
    var representation = {}
    for (key in this) {
        if (key.indexOf("lp_") != 0 ){
            representation[key] = this[key];
        }
    }
    return doXHR(this.self_link,
                 {method: "PUT",
                         sendContent: serializeJSON(representation),
                         headers: {"Content-Type": "application/json"}});
}
Entry.prototype.lp_save = save_entry;

// The collection resource.
function Collection(client, representation, uri) {
    this.init(client, representation, uri);
}
Collection.prototype = new Resource;

function slice_collection(start, size) {
    return this.lp_client.get(this.lp_original_uri, start, size);
}
Collection.prototype.lp_slice = slice_collection;