url = "/+test-webservice-js";
wm.open("url");

// Test methods that operate on URIs.
var client = new LaunchpadClient();

function test_fooThing () {
  var foo = 'asdf';
  jum.assertEquals(foo, 'asdf');
  var bar = 'qwer';
  jum.assertNotEquals(bar, 'asdf');
}
