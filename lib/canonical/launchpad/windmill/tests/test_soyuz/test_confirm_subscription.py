from canonical.launchpad.windmill.testing import lpuser

from windmill.authoring import WindmillTestClient

def test_confirm_subscription():
    """Test the confirm subscription action for subscribers.

    This test ensurens that with Javascript enabled, the 'Confirm
    subscription' link uses the formoverlay to post the activation directly,
    removing one page load.
    """
    client = WindmillTestClient("P3a confirm subscription test")

    # A ppa needs to be private for p3a subscriptions, so login as
    # admin and make celso's ppa private.
    lpuser.FOO_BAR.ensure_login(client)
    client.open(url='http://launchpad.dev:8085/~cprov/+archive/ppa')
    client.waits.forElement(link=u'Administer archive', timeout=u'8000')
    client.click(link=u'Administer archive')
    client.waits.forPageLoad(timeout=u'20000')
    client.check(id=u'field.private')
    client.click(id=u'field.buildd_secret')
    client.type(text=u'secret', id=u'field.buildd_secret')
    client.click(id=u'field.actions.save')
    client.waits.forPageLoad(timeout=u'20000')
    client.open(url='http://launchpad.dev:8085/~cprov')

    # Now login as Celso
    cprov = lpuser.LaunchpadUser('Celso', 'celso.providelo@canonical.com',
        'cprov')
    cprov.ensure_login(client)

    # Now add SamplePerson as a subscriber.
    client.open(
        url='http://launchpad.dev:8085/~cprov/+archive/ppa/+subscriptions')
    client.click(id=u'field.subscriber')
    client.type(text=u'name12', id=u'field.subscriber')
    client.click(id=u'field.actions.add')
    client.waits.forPageLoad(timeout=u'20000')
    client.open(url='http://launchpad.dev:8085/~cprov')

    # Login as Sample Person and confirm the subscription:
    lpuser.SAMPLE_PERSON.ensure_login(client)
    client.open(
        url='http://launchpad.dev:8085/~name12/+archivesubscriptions')

    # Click on the Confirm now link... this brings up the form overlay
    client.click(link=u'Confirm')

    # Click on the form overlay's 'activate' button.
    client.click(name=u'activate')
    client.waits.forPageLoad(timeout=u'20000')

    # Now the subscription has been confirmed.
    client.asserts.assertNode(xpath=u"//div[@id='container']/div[3]/h1")
    client.asserts.assertText(xpath=u"//div[@id='container']/div[3]/h1",
        validator=u"Sample Person's subscription to PPA for Celso Providelo")

