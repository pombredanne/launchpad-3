YUI().use('dom', 'dump', 'lazr.overlay', 'lazr.picker',
          function(Y) {

    var show_widget_id = "%(show_widget_id)s";
    var input_id = "%(input_id)s";

    var picker = new Y.Picker({
        align: {
            points: [Y.WidgetPositionExt.CC,
                      Y.WidgetPositionExt.CC]
        },
        progressbar: true,
        progress: 100,
        headerContent: "<h2>Picker example</h2>",
        steptitle: "Enter search terms",
        zIndex: 1000
        });

    picker.subscribe('save', function (e) {
        Y.log('Got save event.');
        // Y.get() uses CSS3 selectors which don't work with ids containing
        // a period, so we have to use Y.DOM.byId().
        var input = Y.DOM.byId(input_id);
        input.value = e.details[Y.Picker.SEARCH_STRING];
    });

    picker.subscribe('cancel', function (e) {
        Y.log('Got cancel event.');
    });

    picker.after('visibleChange', function () {
        var show_widget_link = Y.get('#' + show_widget_id);
        show_widget_link.set('disabled', picker.get('visible'));
    });

    Y.on('click', function () {
        picker.show();
    }, '#' + show_widget_id);

    // Search for results, create batches and update the display.
    // in the widget.
    var search_handler = function (e) {
        Y.log('Got search event:' + Y.dump(e.details));

        var client = new LP.client.Launchpad();

        success_handler = function (entry) {
            var search_string = e.details[0];
            var selected_batch = e.details[1] || 0;
            var total_size = entry.total_size;
            var start = entry.start;
            var people = entry.entries;

            var results = [];
            Y.Array.each(people, function (person, i) {
                var image_url = '/@@/person';
                if (person.is_team === true) {
                    image_url = '/@@/team';
                }
                results.push({
                    value: person.name,
                    title: person.display_name,
                    css: '',
                    image: image_url,
                    description: 'blah'
                });
            });

            picker.set('results', results);

            // Update the batches only if it's a new search.
            if (e.details[1] === undefined) {
                var batches = [];
                Y.Array.each(results, function (batch, i) {
                    batches.push({
                            name: i+1,
                            value: i,
                        });
                });

                picker.set('batches', batches);
            }
        };

        client.get('/people/', {
            on: {
                success: success_handler,
                failure: function (entry) {
                    alert('Retrieving /people/ failed.');
                }
            }
        });
    };

    picker.after('search', search_handler);

    picker.render();
    picker.hide();
});
