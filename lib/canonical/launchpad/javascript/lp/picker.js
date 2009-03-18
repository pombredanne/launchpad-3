YUI.add('lp.picker', function(Y) {

Y.log('loading lp.picker');

Y.namespace('lp.picker');

Y.lp.picker.addBugTaskAssigneeEditor = function (
    bugtask_uri, content_box_id) {

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

        Y.lp.client.helpers.setBugTaskAssignee(
            bugtask_uri,
            picker_result.value, {
                on: {
                    success: successHandler,
                    failure: failureHandler
                }
            });
    };

    var picker = Y.lp.picker.create(
        'ValidAssignee', save,
        {header: 'Select assignee'});

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
  *                        config.max_description_length truncates long
  *                        description strings.
  */
Y.lp.picker.create = function (vocabulary, save, config) {
    if (config !== undefined) {
        var header = 'Choose an item.';
        if (config.header !== undefined) {
            header = config.header;
        }

        var max_description_length = 40;
        if (config.max_description_length !== undefined) {
            max_description_length = config.max_description_length;
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
        steptitle: "Enter search terms",
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
        var batch_size = 6;
        var offset = batch_size * selected_batch;
        var client = new LP.client.Launchpad();

        success_handler = function (entry) {
            var total_size = entry.total_size;
            var start = entry.start;
            var results = entry.entries;

            Y.Array.each(results, function(entry, i) {
                if (entry.description !== undefined &&
                    entry.description.length > max_description_length) {
                    entry.description = entry.description.substring(
                        0, max_description_length-3) + '...';
                }
            });

            picker.set('results', results);

            // Update the batches only if it's a new search.
            if (e.details[1] === undefined) {
                var batches = [];
                var stop = Math.ceil(total_size / batch_size);
                for (var i=0; i<stop; i++) {
                    batches.push({
                            name: i+1,
                            value: i
                        });
                }

                picker.set('batches', batches);
            }
        };

        var qs = '';
        qs = LP.client.append_qs(qs, 'name', vocabulary);
        qs = LP.client.append_qs(qs, 'search_text', search_text);
        qs = LP.client.append_qs(qs, 'size', batch_size);
        qs = LP.client.append_qs(qs, 'offset', offset);

        var uri = '/+vocabulary?' + qs;

        // wrap_resource_on_success parses the results if it's JSON,
        // and passes the parsed data to the success_handler.
        Y.io(uri, {
            'arguments': [client, uri, success_handler],
            headers: {'Accept': 'application/json'},
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
