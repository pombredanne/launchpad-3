YUI.add('lp.milestonetable', function(Y) {
    Y.log('loading lp.milestonetable');
    var self = Y.namespace('lp.milestonetable');

    self._milestone_row_uri_template = null;
    self._tbody = null;

    self._prepend_node = function(parent_node, child_node) {
        var children = parent_node.get('children');
        if (children.length === 0) {
            parent_node.appendChild(child_node);
        } else {
            parent_node.insertBefore(child_node, children.item(0));
            }
        };

    self._ensure_table_is_seen = function(tbody) {
        table = tbody.ancestor();
        table.removeClass('unseen');
        };

    self._clear_add_handlers = function(data) {
        data.success_handle.detach();
        data.failure_handle.detach();
        };

    self._on_add_success = function(id, response, data) {
        var row = Y.Node.create(Y.Lang.trim(response.responseText));
        self._ensure_table_is_seen(data.tbody);
        self._prepend_node(data.tbody, row);
        Y.lazr.anim.green_flash({node: row}).run();
        self._clear_add_handlers(data);
        };

    self._on_add_failure = function(id, response, data) {
        var row = Y.Node.create(Y.substitute(
            '<tr><td colspan="0">' +
            'Could not retrieve milestone {name}</td></tr>', data));
        self._ensure_table_is_seen(data.tbody);
        self._prepend_node(data.tbody, row);
        Y.lazr.anim.red_flash({node: row}).run();
        self._clear_add_handlers(data);
        };

    self._setup_milestone_event_data = function(parameters, tbody) {
        var data = {
            name: parameters.name,
            tbody: tbody
            };
        data.success_handle = Y.on(
            'io:success', self._on_add_success, this, data);
        data.failure_handle = Y.on(
            'io:failure', self._on_add_failure, this, data);
        return data;
        };

    self.get_milestone_row = function(parameters) {
        self._setup_milestone_event_data(parameters, self._tbody);
        var milestone_row_uri = Y.substitute(
            self._milestone_row_uri_template, parameters);
        Y.io(milestone_row_uri);
        };

    self.setup =  function(config) {
        if (config === undefined) {
            throw new Error(
                "Missing setup config for milestonetable.");
            }
        if (config.milestone_row_uri_template === undefined ||
            config.milestone_rows_id === undefined ) {
            throw new Error(
                "Undefined properties in setup config for milestonetable.");
            }
        self._milestone_row_uri_template = config.milestone_row_uri_template;
        self._tbody = Y.get(config.milestone_rows_id);
        if (self._tbody === null) {
            throw new Error(
                Y.substitute("'{milestone_rows_id}' not in page.", config));
            }
        };

}, '0.1', {
requires: [
    'node', 'io-base', 'substitute', 'lazr.anim'
    ]});

