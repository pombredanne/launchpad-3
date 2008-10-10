// An AJAX client that runs against Launchpad's web service.

// Generally useful functions.


var HTTP_CREATED = 201;
var HTTP_NOT_FOUND = 404;

function extract_webservice_start(url) {
    /* Extract the service's root URI from any Launchpad web service URI. */
    var host_start = url.indexOf('//');
    var host_end = url.indexOf('/', host_start+2);
    return url.substring(0, host_end+1) + 'api/beta/';
}

function start_and_size(data, start, size) {
    /* Create a query string with values for ws.start and/or ws.size. */
    if (start != undefined) {
        data = append_qs(data, "ws.start", start);
    }
    if (size != undefined) {
        data = append_qs(data, "ws.size", size);
    }
    return data;
}

function append_qs(qs, key, value) {
    /* Append a key-value pair to a query string. */
    if (qs == undefined) {
        qs = "";
    }
    if (qs.length > 0) {
        qs += '&';
    }
    qs += escape(key) + "=" + escape(value);
    return qs;
}

function wrap_resource_on_success(unknown, response, arguments) {
    var Y = arguments[0];
    var client = arguments[1];
    var uri = arguments[2];
    var old_on_success = arguments[3];
    var representation = Y.JSON.parse(response.responseText);
    var wrapped = client.wrap_resource(uri, representation);
    return old_on_success(wrapped);
}


// The Launchpad client itself.

function LaunchpadClient() {
    /* A client that makes HTTP requests to Launchpad's web service. */
}
LaunchpadClient.prototype = {
    'base': extract_webservice_start(location.href),
    'get': function (uri, on, start, size, data) {
        /* Get the current state of a resource.

           :param start: If the resource is a collection, where in the
               collection to start serving entries.
           :param size: If the resource is a collection, how many
               entries to serve.
        */
        if (uri.indexOf("http") != 0) {
            uri = this.base + uri;
        }
        if (data == undefined) {
            data = "";
        }
        if (start != undefined || size != undefined) {
            data = start_and_size(data, start, size);
        }

        var old_on_success = on.success;
        on.success = wrap_resource_on_success;

        var client = this;
        YUI().use('io', 'json-parse', function(Y) {
                var config = { on: on,
                               arguments: [Y, client, uri, old_on_success],
                               data: data};
                Y.io(uri, config);
            }
            )
    },

    'named_get' : function(uri, operation_name, on, parameters,
                           start, size) {
        /* Retrieve the value of a named GET operation on the given URI. */
        var data = append_qs("", "ws.op", operation_name);
        for (name in parameters) {
            data = append_qs(data, name, parameters[name]);
        }
        return this.get(uri, on, start, size, data);
    },

    'named_post' : function (uri, operation_name, on, parameters) {
        /* Perform a named POST operation on the given URI. */
        if (uri.indexOf("http") != 0) {
            uri = this.base + uri;
        }
        var data = append_qs(data, "ws.op", operation_name);
        for (name in parameters) {
            data = append_qs(data, name, parameters[name]);
        }

        var old_on_success = on.success;
        on.success = wrap_resource_on_success;

        var client = this;
        YUI().use('io', 'json-parse', function(Y) {
                var config = { method: "POST",
                               on: on,
                               arguments: [Y, client, uri, old_on_success],
                               data: data};
                Y.io(uri, config);
            }
            )
    },

    'wrap_resource': function(uri, representation) {
        /* Given a representation, turn it into a subclass of Resource. */
        var obj = undefined;
        if (representation == undefined) {
            return representation;
        }
        if (representation.lp_redirect_location != undefined) {
            uri = representation.lp_redirect_location;
        }
        if (representation.resource_type_link == undefined) {
            // This is a non-entry object returned by a named operation.
            // It's either a list or a random JSON object.
            if (representation.total_size != undefined) {
                // It's a list. Treat it as a collection; it should be slicable.
                obj = new Collection(this, representation, uri);
            }
            // It's a random JSON object. Leave it alone.
        } else if (representation.resource_type_link.search(/\/#service-root$/)
                   != -1) {
            obj = new Launchpad(this, representation, uri);
        } else if (representation.total_size == undefined) {
            obj = new Entry(this, representation, uri);
        } else {
            obj = new Collection(this, representation, uri);
        }
        return obj;
    },
}


function Resource() {
    /* The base class for objects retrieved from Launchpad's web service. */
}
Resource.prototype = {
    'init': function(client, representation, uri) {
        /* Initialize a resource with its representation and URI. */
        this.lp_client = client;
        this.lp_original_uri = uri;
        for (key in representation) { this[key] = representation[key]; }
    },

    follow_link: function(link_name, on) {
        /* Return the object at the other end of the named link. */
        var url = this[link_name + '_link'];
        if (url == undefined) {
            url = this[link_name + '_collection_link'];
        }
        if (url == undefined) {
            throw new Error("No such link: " + link_name);
        }

        // TODO: If the response is 404, we have a hosted file.
        // Hack the error hook a la treat_404_as_hosted_file.
        this.lp_client.get(url, on);
    },

    named_get: function(operation_name, on, parameters, start, size) {
        /* Get the result of a named GET operation on this resource. */
        return this.lp_client.named_get(this.lp_original_uri, operation_name,
                                        on, parameters, start, size);
    }

}

// The service root resource.
function Launchpad(client, representation, uri) {
    /* The root of the Launchpad web service. */
    this.init(client, representation, uri);
}
Launchpad.prototype = new Resource;

function Collection(client, representation, uri) {
    /* A grouped collection of objets from the Launchpad web service. */
    this.init(client, representation, uri);
}
Collection.prototype = new Resource;

Collection.prototype.lp_slice = function(on, start, size) {
    /* Retrieve a subset of the collection.

       :param start: Where in the collection to start serving entries.
       :param size: How many entries to serve.
    */
    return this.lp_client.get(this.lp_original_uri, on, start, size);
}


function Entry(client, representation, uri) {
    /* A single object from the Launchpad web service. */
    this.init(client, representation, uri);
}
Entry.prototype = new Resource;

Entry.prototype.lp_save = function(on) {
    /* Write modifications to this entry back to the web service. */
    var representation = {}
    for (key in this) {
        if (key.indexOf("lp_") != 0 ){
            representation[key] = this[key];
        }
    }
    var entry = this;
    YUI().use('io', 'json-stringify', function(Y) {
            var data = Y.JSON.stringify(representation);
            arguments = [Y, entry.lp_client, entry.self_link];
            var config = { method: "PUT",
                           on: on,
                           headers: {"Content-Type": "application/json"},
                           arguments: arguments,
                           data: data};
            Y.io(entry.self_link, config);
        }
        )
}

