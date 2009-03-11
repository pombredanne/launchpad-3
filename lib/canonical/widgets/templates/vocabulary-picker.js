YUI().use('node', 'lp.picker', function(Y) {
    var show_widget_node = Y.get('#%(show_widget_id)s');
    var save = function (result) {
        Y.DOM.byId('%(input_id)s').value = result['value'];
    };
    var config = {
        header: '%(header)s',
        max_description_length: '%(max_description_length)s'
    };
    Y.lp.picker.add('%(vocabulary)s', show_widget_node, save, config);
});
