"""Use the inherited HTTP proxy for Playwright's separate HTTP client.

Chromium and APIRequestContext do not necessarily inherit the same transport.
Keep TLS verification on; respect the existing proxy and NO_PROXY settings.
No response substitution, route interception, DNS override or policy change.
"""
from urllib.parse import unquote, urlsplit
from urllib.request import getproxies, proxy_bypass


def new_api_context(playwright, target):
    url = urlsplit(target)
    proxies = getproxies()
    proxy_url = None if proxy_bypass(url.netloc) else proxies.get(url.scheme, proxies.get('all'))
    options = {}
    if proxy_url:
        proxy = urlsplit(proxy_url)
        host = '['+proxy.hostname+']' if ':' in proxy.hostname else proxy.hostname
        server = proxy.scheme+'://'+host+(':'+str(proxy.port) if proxy.port else '')
        options['proxy'] = {'server': server}
        if proxy.username is not None:
            options['proxy']['username'] = unquote(proxy.username)
        if proxy.password is not None:
            options['proxy']['password'] = unquote(proxy.password)
    return playwright.request.new_context(**options)
