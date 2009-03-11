YUI.add('lp.picker', function(Y) {
    Y.log('loading lp.picker');

    Y.namespace('lp.picker');

    /**
     * Adds the on-event handler to the show_widget_node, and it calls
     * the save function when a value is chosen.
     *
     * @module lp
     * @submodule widget.picker
     * @requires dom, dump, lazr.overlay, lazr.picker
     * @method add
     * @param {String} vocabulary Name of the vocabulary to query.
     * @param {Node} show_widget_node Button or link which displays widget.
     * @param {Function} save Function which takes a single string argument.
     * @param {Function} header Optional argument to override text at the top
     *                          of the widget.
     */
    Y.lp.picker.add = function (vocabulary, show_widget_node, save, header) {
        if (header === undefined) {
            header = 'Choose an item.';
        }

        if (typeof vocabulary != 'string') {
            throw new TypeError(
                "vocabulary argument for Y.lp.picker.add() must be a string: "
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
            save(e.details[Y.Picker.SEARCH_STRING]);
        });

        picker.subscribe('cancel', function (e) {
            Y.log('Got cancel event.');
        });

        picker.after('visibleChange', function () {
            show_widget_node.set('disabled', picker.get('visible'));
        });

        Y.on('click', function () {
            picker.show();
        }, show_widget_node);

        // Search for results, create batches and update the display.
        // in the widget.
        var search_handler = function (e) {
            Y.log('Got search event:' + Y.dump(e.details));
            var search_text = e.details[0];
            var selected_batch = e.details[1] || 0;
            var batch_size = 3;
            var offset = batch_size * selected_batch;
            var client = new LP.client.Launchpad();

            success_handler = function (entry) {
                var total_size = entry.total_size;
                var start = entry.start;
                var results = entry.entries;

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
    };
}, '0.1', {requires: ['io', 'dom', 'dump', 'lazr.overlay', 'lazr.picker']});
