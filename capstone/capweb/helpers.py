import json
from contextlib import contextmanager
from functools import wraps

import requests
import django_hosts
from django.conf import settings
from django.core.cache import caches
from django.db import transaction, connections, OperationalError
from django.urls import NoReverseMatch
from django_hosts.resolvers import get_host_patterns


def cache_func(key, timeout=None, cache_name='default'):
    """
        Decorator to cache decorated function's output according to a custom key.
        `key` should be a lambda that takes the decorated function's arguments and returns a cache key.
    """
    cache = caches[cache_name]
    def decorator(func):
        @wraps(func)
        def decorated(*args, **kwargs):
            cache_key = key(*args, **kwargs)

            # return existing value, if any
            value = cache.get(cache_key)
            if value is not None:
                print("Got existing for", cache_key)
                return value
            print("Making new for", cache_key)

            # cache new value
            value = func(*args, **kwargs)
            cache.set(cache_key, value, timeout)
            return value
        return decorated
    return decorator

@cache_func(
    key=lambda section: 'get_data_from_lil_site:%s' % section,
    timeout=settings.CACHED_COUNT_TIMEOUT
)
def get_data_from_lil_site(section="news"):
    response = requests.get("https://lil.law.harvard.edu/api/%s/caselaw-access-project/" % section)
    content = response.content.decode()
    start_index = content.index('(')
    if section == "contributors":
        # account for strangely formatted response
        end_index = content.index(']}') + 2
    else:
        end_index = -1
    data = json.loads(content.strip()[start_index + 1:end_index])
    return data[section]

def reverse(*args, **kwargs):
    """
        Wrap django_hosts.reverse() to try all known hosts.
    """
    # if host is provided, just use that
    if 'host' in kwargs:
        return django_hosts.reverse(*args, **kwargs)

    # try each host
    hosts = get_host_patterns()
    for i, host in enumerate(reversed(hosts)):
        kwargs['host'] = host.name
        try:
            return django_hosts.reverse(*args, **kwargs)
        except NoReverseMatch:
            # raise NoReverseMatch only after testing final host
            if i == len(hosts)-1:
                raise


def show_toolbar_callback(request):
    """
        Whether to show django-debug-toolbar.
        This adds an optout for urls with ?no_toolbar
    """
    from debug_toolbar.middleware import show_toolbar
    return False if 'no_toolbar' in request.GET else show_toolbar(request)


class StatementTimeout(Exception):
    pass

@contextmanager
def statement_timeout(timeout, db="default"):
    """
        Context manager to kill queries if they take longer than `timeout` seconds.
        Timed-out queries will raise StatementTimeout.
    """
    with transaction.atomic(using=db):
        with connections[db].cursor() as cursor:
            cursor.execute("SHOW statement_timeout")
            original_timeout = cursor.fetchone()[0]
            cursor.execute("SET LOCAL statement_timeout = '%ss'" % timeout)
            try:
                yield
            except OperationalError as e:
                if e.args[0] == 'canceling statement due to statement timeout\n':
                    raise StatementTimeout()
                raise
            # reset to default, in case we're in a nested transaction
            cursor.execute("SET LOCAL statement_timeout = %s", [original_timeout])