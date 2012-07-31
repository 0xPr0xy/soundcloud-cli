import codecs
import urllib

import requests

try:
    from mimetools import choose_boundary
except ImportError:
    from requests.packages.urllib3.packages.mimetools_choose_boundary import choose_boundary

from io import BytesIO

from requests.packages.urllib3.packages import six
from requests.packages.urllib3.packages.six import b
from requests.packages.urllib3.filepost import get_content_type

import soundcloud

writer = codecs.lookup('utf-8')[3]


def encode_multipart_formdata(fields, boundary=None):
    """Fix bug in multipart/form-data POST request handling.

    For some reason, the specific combination of Rack + Ruby + Rails versions
    that we are using in production has trouble handling multipart/form-data
    POST requests where the non-binary parts have a Content-Type header. To
    get around this, we just monkey patch the ```encode_multipart_formdata```
    function in ```urllib3``` and modify it to *not* set the Content-Type
    header on non-binary parts.
    """
    body = BytesIO()
    if boundary is None:
        boundary = choose_boundary()

    for fieldname, value in six.iteritems(fields):
        body.write(b('--%s\r\n' % (boundary)))

        if isinstance(value, tuple):
            filename, data = value
            writer(body).write('Content-Disposition: form-data; name="%s"; '
                               'filename="%s"\r\n' % (fieldname, filename))
            body.write(b('Content-Type: %s\r\n\r\n' %
                         (get_content_type(filename))))
        else:
            data = value
            writer(body).write(
                'Content-Disposition: form-data; name="%s"\r\n\r\n' % (
                    fieldname))

        if isinstance(data, int):
            data = str(int)  # Backwards compatibility

        if isinstance(data, six.text_type):
            writer(body).write(data)
        else:
            body.write(data)

        body.write(b'\r\n')

    body.write(b('--%s--\r\n' % (boundary)))

    content_type = b('multipart/form-data; boundary=%s' % boundary)

    return body.getvalue(), content_type

# monkey patch urllib3 to use our modified function
requests.models.encode_multipart_formdata = encode_multipart_formdata


def extract_files_from_dict(d):
    """Return any file objects from the provided dict.

    >>> extract_files_from_dict({
    ... 'oauth_token': 'foo',
    ... 'track': {
    ...   'title': 'bar',
    ...   'asset_data': file('setup.py', 'rb')
    ...  }})  # doctest:+ELLIPSIS
    {'track': {'asset_data': <open file 'setup.py', mode 'rb' at 0x...}}
    """
    files = {}
    for key, value in d.iteritems():
        if isinstance(value, dict):
            files[key] = extract_files_from_dict(value)
        elif isinstance(value, file):
            files[key] = value
    return files


def remove_files_from_dict(d):
    """Return the provided dict with any file objects removed.

    >>> remove_files_from_dict({
    ...   'oauth_token': 'foo',
    ...   'track': {
    ...       'title': 'bar',
    ...       'asset_data': file('setup.py', 'rb')
    ...   }
    ... })  # doctest:+ELLIPSIS
    {'track': {'title': 'bar'}, 'oauth_token': 'foo'}
    """
    file_free = {}
    for key, value in d.iteritems():
        if isinstance(value, dict):
            file_free[key] = remove_files_from_dict(value)
        elif not isinstance(value, file):
            file_free[key] = value
    return file_free


def namespaced_query_string(d, prefix=""):
    """Transform a nested dict into a string with namespaced query params.

    >>> namespaced_query_string({
    ...  'oauth_token': 'foo',
    ...  'track': {'title': 'bar', 'sharing': 'private'}})  # doctest:+ELLIPSIS
    {'track[sharing]': 'private', 'oauth_token': 'foo', 'track[title]': 'bar'}
    """
    qs = {}
    prefixed = lambda k: prefix and "%s[%s]" % (prefix, k) or k
    for key, value in d.iteritems():
        if isinstance(value, dict):
            qs.update(namespaced_query_string(value, prefix=key))
        else:
            qs[prefixed(key)] = value
    return qs


def make_request(method, url, params):
    """Make an HTTP request, formatting params as required."""
    empty = []
    for key, value in params.iteritems():
        if value is None:
            empty.append(key)
    for key in empty:
        del params[key]

    # allow caller to disable automatic following of redirects
    allow_redirects = params.get('allow_redirects', True)

    kwargs = {
        'allow_redirects': allow_redirects,
        'headers': {
            'User-Agent': soundcloud.USER_AGENT
        }
    }
    # options, not params
    if 'verify_ssl' in params:
        if params['verify_ssl'] is False:
            kwargs['verify'] = params['verify_ssl']
        del params['verify_ssl']
    if 'proxies' in params:
        kwargs['proxies'] = params['proxies']
        del params['proxies']
    if 'allow_redirects' in params:
        del params['allow_redirects']

    files = namespaced_query_string(extract_files_from_dict(params))
    data = namespaced_query_string(remove_files_from_dict(params))

    request_func = getattr(requests, method, None)
    if request_func is None:
        raise TypeError('Unknown method: %s' % (method,))

    if method == 'get':
        qs = urllib.urlencode(data)
        result = request_func('%s?%s' % (url, qs), **kwargs)
    else:
        kwargs['data'] = data
        if files:
            kwargs['files'] = files
        result = request_func(url, **kwargs)

    # if redirects are disabled, don't raise for 301 / 302
    if result.status_code in [301, 302]:
        if allow_redirects:
            result.raise_for_status()
    else:
        result.raise_for_status()
    return result
