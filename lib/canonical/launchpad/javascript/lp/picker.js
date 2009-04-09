YUI.add('lp.picker', function(Y) {

Y.log('loading lp.picker');

Y.namespace('lp.picker');

var BATCH_SIZE = 6;
var MAX_MATCHES = 100;

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

        var success_handler = function (ignore, response, args) {
            var entry = Y.JSON.parse(response.responseText);
            var total_size = entry.total_size;
            var start = entry.start;
            var results = entry.entries;

            if (total_size > MAX_MATCHES)  {
                picker.set('error',
                    'Too many matches. Please try to narrow your search');
                // Display a single empty result item so that the picker
                // doesn't say that no items matched, which is contradictory.
                picker.set('results', [{}]);
                picker.set('batches', []);
            } else {
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
            }
        };

        var qs = '';
        qs = LP.client.append_qs(qs, 'name', vocabulary);
        qs = LP.client.append_qs(qs, 'search_text', search_text);
        qs = LP.client.append_qs(qs, 'batch', BATCH_SIZE);
        qs = LP.client.append_qs(qs, 'start', start);

        var uri = '/+huge-vocabulary?' + qs;

        Y.io(uri, {
            headers: {'Accept': 'application/json'},
            timeout: 20000,
            on: {
                success: success_handler,
                failure: function (arg) {
                    picker.set('error', 'Loading results failed.');
                    Y.log("Loading " + uri + " failed.");
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
    'io', 'dom', 'dump', 'lazr.picker', 'lazr.activator', 'json-parse',
    'lp.client.helpers'
    ]});
