YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false, fetchCSS: false
    }).use('test', 'console', 'lp.bugs.filebug_dupefinder',
        'node-event-simulate', function(Y) {

var suite = new Y.Test.Suite("lp.bugs.filebug_dupefinder Tests");
var module = Y.lp.bugs.filebug_dupefinder;

/*
 * A wrapper for the Y.Event.simulate() function.  The wrapper accepts
 * CSS selectors and Node instances instead of raw nodes.
 */
function simulate(widget, selector, evtype, options) {
    var node_to_use = widget;
    if (selector !== undefined) {
        node_to_use = widget.one(selector);
    }
    var rawnode = Y.Node.getDOMNode(node_to_use);
    Y.Event.simulate(rawnode, evtype, options);
}

function IOStub(){
    if (!(this instanceof IOStub)) {
        throw new Error("Constructor called as a function");
    }
    this.io = function(url, config) {
        this._call('io', config, arguments);
    };
}

IOStub.prototype._call = function(name, config, args) {
    config.on.success(0, '', {});
};

suite.add(new Y.Test.Case({
    name: 'Test filebug form manipulation.',

    setUp: function() {
        var config = {};
        config.yio = new IOStub();
        module.setup_config(config);
        module.setup_dupe_finder();
    },

    tearDown: function() {
    },

    test_search_shows_filebug_form: function() {
        var search_button = Y.one(Y.DOM.byId('field.actions.search'));
        simulate(search_button, undefined, 'click');
    }

}));

var handle_complete = function(data) {
    status_node = Y.Node.create(
        '<p id="complete">Test status: complete</p>');
    Y.one('body').appendChild(status_node);
    };
Y.Test.Runner.on('complete', handle_complete);
Y.Test.Runner.add(suite);

var console = new Y.Console({newestOnTop: false});
console.render('#log');

Y.on('domready', function() {
    Y.Test.Runner.run();
});
});
