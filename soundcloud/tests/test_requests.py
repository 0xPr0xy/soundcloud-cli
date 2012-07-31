from contextlib import contextmanager

import fudge
import soundcloud

from nose.tools import raises, assert_raises
from requests.exceptions import HTTPError

from soundcloud.tests.utils import MockResponse


@contextmanager
def response_status(fake_http_request, status):
    response = MockResponse('{}', status_code=status)
    fake_http_request.expects_call().returns(response)
    yield


@fudge.patch('requests.get')
def test_bad_responses(fake):
    """Anything in the 400 or 500 range should raise an exception."""
    client = soundcloud.Client(client_id='foo', client_secret='foo')
    for status in range(400, 423):
        with response_status(fake, status):
            assert_raises(HTTPError, lambda: client.get('/me'))
    for status in (500, 501, 502, 503, 504, 505):
        with response_status(fake, status):
            assert_raises(HTTPError, lambda: client.get('/me'))

@fudge.patch('requests.get')
def test_ok_response(fake):
    """A 200 range response should be fine."""
    client = soundcloud.Client(client_id='foo', client_secret='foo')
    for status in (200, 201, 202, 203, 204, 205, 206):
        with response_status(fake, status):
            user = client.get('/me')

@fudge.patch('requests.get')
def test_redirects(fake):
    """Make sure 300 responses raise an exception.

    Note: ```requests``` transparently attempts redirects so if we get
    this back it means the caller has disabled redirects or the max
    number has been reached.
    """
    client = soundcloud.Client(client_id='foo', client_secret='foo')
    for status in (300, 301, 302, 303, 304, 305, 307):
        with response_status(fake, status):
            assert_raises(HTTPError, lambda: client.get('/me'))
