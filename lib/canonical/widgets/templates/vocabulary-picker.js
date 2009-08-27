YUI().use('node', 'lp.picker', function(Y) {
    if (Y.UA.ie) {
        return;
    }

    // Args from python.
    var args = %s;

    var show_widget_node = Y.get('#' + args.show_widget_id);
    var save = function (result) {
        Y.DOM.byId(args.input_id).value = result.value;
    };
    var config = {
        header: args.header,
        step_title: args.step_title,
        extra_no_results_message: args.extra_no_results_message
    };
    var picker = Y.lp.picker.create(args.vocabulary, save, config);
    if (config.extra_no_results_message !== null) {
        picker.before('resultsChange', function (e) {
            var new_results = e.details[0].newVal;
            if (new_results.length === 0) {
                picker.set('footer_slot',
                           Y.Node.create(config.extra_no_results_message));
            }
            else {
                picker.set('footer_slot', null);
            }
        });
    }
    show_widget_node.set('innerHTML', 'Choose&hellip;');
    show_widget_node.addClass('js-action');
    show_widget_node.get('parentNode').removeClass('unseen');
    show_widget_node.on('click', function (e) {
        picker.show();
        e.preventDefault();
    });
});
