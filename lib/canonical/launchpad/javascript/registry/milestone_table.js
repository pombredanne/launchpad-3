YUI.add('lp.milestonetable', function(Y) {
    Y.log('loading lp.milestonetable');
    var milestonetable = Y.namespace('lp.milestonetable');

    var milestone_row_uri_template;
    var milestone_rows_id;

    var clear_append_milestone_handlers = function(data) {
        data.success_handle.detach();
        data.failure_handle.detach();
    };

    var prepend_node = function(parent_node, child_node) {
        var children = parent_node.get('children');
        if (children.length === 0) {
            parent_node.appendChild(child_node);
        } else {
            parent_node.insertBefore(child_node, children.item(0));
        }
    };

    var append_milestone = function(id, response, data) {
        var row = Y.Node.create(Y.Lang.trim(response.responseText));
        prepend_node(data.tbody, row);
        Y.lazr.anim.green_flash({node: row}).run();
        clear_append_milestone_handlers(data);
    };

    var append_failure = function(id, response, data) {
        var row = Y.Node.create(Y.substitute(
            '<tr><td colspan="0">' +
            'Could not retrieve milestone {name}</td></tr>', data));
        prepend_node(data.tbody, row);
        Y.lazr.anim.red_flash({node: row}).run();
        clear_append_milestone_handlers(data);
    };

    milestonetable.get_milestone_row = function(parameters) {
        var milestone_row_uri = Y.substitute(
            milestone_row_uri_template, parameters);
        var data = {
            name: parameters.name,
            tbody: Y.get(milestone_rows_id),
            seen: 0
            };
        data.success_handle = Y.on(
            'io:success', append_milestone, this, data);
        data.failure_handle = Y.on(
            'io:failure', append_failure, this, data);
        Y.io(milestone_row_uri);
    };

    milestonetable.setup =  function(config) {
        if (config === undefined) {
            throw new Error(
                "Missing setup config for milestonetable.");
        }
        if (config.milestone_row_uri_template === undefined ||
            config.milestone_rows_id === undefined ) {
            throw new Error(
                "setup config for milestonetable has undefined properties.");
        }
        milestone_row_uri_template = config.milestone_row_uri_template;
        milestone_rows_id = config.milestone_rows_id;
    };

}, '0.1', {
requires: [
    'node', 'io-base', 'substitute', 'lazr.anim'
    ]});

