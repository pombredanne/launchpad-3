YUI.add('lp.ordering.test', function(Y) {

var basic_test = Y.namespace('lp.ordering.test');

var suite = new Y.Test.Suite('Basic Tests');

suite.add(new Y.Test.Case({

    name: 'basic_starter_test',

    test_basic_test: function() {
        Y.Assert.isTrue(true);
    }

}));

basic_test.suite = suite

});

