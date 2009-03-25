YUI().use('node', 'lp.picker', function(Y) {
    var show_widget_node = Y.get('#%(show_widget_id)s');
    var save = function (result) {
        Y.DOM.byId('%(input_id)s').value = result.value;
    };
    var config = {
        header: '%(header)s',
        step_title: '%(step_title)s',
    };
    var picker = Y.lp.picker.create('%(vocabulary)s', save, config);
    show_widget_node.on('click', function (e) {
        picker.show();
    });
});
