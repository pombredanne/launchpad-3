YUI.add('lp.picker', function(Y) {

Y.log('loading lp.picker');

Y.namespace('lp.picker');

var BATCH_SIZE = 6;

/* Add a picker widget which will PATCH a given attribute on
 * a given resource.
 *
 * @method addPickerPatcher
 * @param {String} resource_uri The object being modified.
 * @param {String} attribute_uri_base Canonical URI prefix.
 * @param {String} attribute_name The attribute on the resource being
 *                                modified.
 * @param {String} content_box_id
 */
Y.lp.picker.addPickerPatcher = function (
    resource_uri, attribute_uri_base, attribute_name, content_box_id) {

    var activator = new Y.lazr.activator.Activator(
        {content_box: Y.get('#' + content_box_id)});

    var save = function (picker_result) {
        activator.renderProcessing();
        var successHandler = function (e) {
            var link = Y.Node.create('<a/>');
            var icon = Y.Node.create('<img/>');
            icon.set('src', picker_result.image);
            link.appendChild(icon);
            link.appendChild(Y.Node.create(' ' + picker_result.title));
            link.set('href',
                '/~' + picker_result.value + '/+assignedbugs');
            activator.renderSuccess(link);
        };

        var failureHandler = function (xid, response, args) {
            activator.renderFailure(
                Y.Node.create(
                    '<div>' + response.statusText +
                        '<pre>' + response.responseText + '</pre>' +
                    '</div>'));
        };

        var patch_payload = {};
        patch_payload[attribute_name] = LP.client.get_absolute_uri(
            attribute_uri_base + picker_result.value);

        // LP.client won't insert 'api/beta' into an absolute url.
        var index = resource_uri.indexOf('//');
        if (index != -1) {
            index = resource_uri.indexOf('/', index+2);
            resource_uri = resource_uri.substring(index);
        }

        var client =  new LP.client.Launchpad();
        client.patch(resource_uri, patch_payload, {
                on: {
                    success: successHandler,
                    failure: failureHandler
                }
            });
    };

    var picker = Y.lp.picker.create(
        'ValidAssignee', save, {
            header: 'Choose assignee',
            step_title: 'Search for people or teams',
        });

    activator.subscribe('act', function (e) {
        picker.show();
    });
    activator.render();
};

/**
  * Creates a picker widget that has already been rendered and hidden.
  *
  * @requires dom, dump, lazr.overlay, lazr.picker
  * @method create
  * @param {String} vocabulary Name of the vocabulary to query.
  * @param {Function} save Function which takes a single string argument.
  * @param {Object} config Object literal of config name/value pairs.
  *                        config.header is a line of text at the top of
  *                        the widget.
  *                        config.step_title overrides the subtitle.
  *                        description strings.
  */
Y.lp.picker.create = function (vocabulary, save, config) {
    if (config !== undefined) {
        var header = 'Choose an item.';
        if (config.header !== undefined) {
            header = config.header;
        }

        var step_title = "Enter search terms";
        if (config.step_title !== undefined) {
            step_title = config.step_title;
        }
    }

    if (typeof vocabulary != 'string') {
        throw new TypeError(
            "vocabulary argument for Y.lp.picker.create() must be a string: "
            + vocabulary);
    }

    var picker = new Y.Picker({
        align: {
            points: [Y.WidgetPositionExt.CC,
                        Y.WidgetPositionExt.CC]
        },
        progressbar: true,
        progress: 100,
        headerContent: "<h2>" + header + "</h2>",
        steptitle: step_title,
        zIndex: 1000
        });

    picker.subscribe('save', function (e) {
        Y.log('Got save event.');
        // Y.get() uses CSS3 selectors which don't work with ids containing
        // a period, so we have to use Y.DOM.byId().
        save(e.details[Y.Picker.SAVE_RESULT]);
    });

    picker.subscribe('cancel', function (e) {
        Y.log('Got cancel event.');
    });

    // Search for results, create batches and update the display.
    // in the widget.
    var search_handler = function (e) {
        Y.log('Got search event:' + Y.dump(e.details));
        var search_text = e.details[0];
        var selected_batch = e.details[1] || 0;
        var start = BATCH_SIZE * selected_batch;
        var client = new LP.client.Launchpad();

        success_handler = function (entry) {
            var total_size = entry.total_size;
            var start = entry.start;
            var results = entry.entries;

            picker.set('results', results);

            // Update the batches only if it's a new search.
            if (e.details[1] === undefined) {
                var batches = [];
                var stop = Math.ceil(total_size / BATCH_SIZE);
                if (stop > 1) {
                    for (var i=0; i<stop; i++) {
                        batches.push({
                                name: i+1,
                                value: i
                            });
                    }
                }

                picker.set('batches', batches);
            }
        };

        var qs = '';
        qs = LP.client.append_qs(qs, 'name', vocabulary);
        qs = LP.client.append_qs(qs, 'search_text', search_text);
        qs = LP.client.append_qs(qs, 'batch', BATCH_SIZE);
        qs = LP.client.append_qs(qs, 'start', start);

        var uri = '/+huge-vocabulary?' + qs;

        // wrap_resource_on_success parses the results if it's JSON,
        // and passes the parsed data to the success_handler.
        Y.io(uri, {
            'arguments': [client, uri, success_handler],
            headers: {'Accept': 'application/json'},
            timeout: 20000,
            on: {
                success: LP.client.wrap_resource_on_success,
                failure: function (arg) {
                    picker.set('error', 'Loading results failed.');
                    Y.log("Loading " + uri + " failed.");
                    LP.log_object(arg, 'Error');
                }
            }
        });
    };

    picker.after('search', search_handler);

    picker.render();
    picker.hide();
    return picker;
};

}, '0.1', {
requires: [
    'io', 'dom', 'dump', 'lazr.picker', 'lazr.activator',
    'lp.client.helpers'
    ]});
