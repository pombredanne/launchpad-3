YUI({
  base: '/+icing/yui/',
  filter: 'raw', combine: false, fetchCSS: false
}).use('test', 'lp.testing.serverfixture',
       function(Y) {

var suite = new Y.Test.Suite("lp.testing.yuixhr facet Tests");
var serverfixture = Y.lp.testing.serverfixture;


/**
 * Test how the yuixhr server fixture handles specified facets.
 */
suite.add(new Y.Test.Case({
  name: 'Serverfixture facet tests',

  tearDown: function() {
    serverfixture.teardown(this);
  },

  test_facet_was_honored: function() {
    Y.Assert.areEqual('bugs.launchpad.dev', Y.config.doc.location.hostname);
  }
}));

serverfixture.run(suite);
});
