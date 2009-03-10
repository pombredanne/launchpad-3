YUI().use('node', 'lp.picker', function(Y) {
    var show_widget_node = Y.get('#%(show_widget_id)s');
    Y.lp.picker.add(show_widget_node, function (value) {
        Y.DOM.byId('%(input_id)s').value = value;
    });
});
