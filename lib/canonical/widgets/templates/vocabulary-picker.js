YUI().use('node', 'lp.picker', function(Y) {
    var show_widget_node = Y.get('#%(show_widget_id)s');
    var save = function (value) {
        Y.DOM.byId('%(input_id)s').value = value;
    };
    Y.lp.picker.add('%(vocabulary)s', show_widget_node, save, '%(header)s');
});
