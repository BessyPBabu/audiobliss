import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60  # 15 minutes


def _cache_key(prefix, identifier):
    return f"throttle:{prefix}:{identifier}".lower()


def is_locked_out(prefix, identifier):
    return cache.get(_cache_key(prefix, identifier), 0) >= MAX_ATTEMPTS


def register_failed_attempt(prefix, identifier):
    key = _cache_key(prefix, identifier)
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, LOCKOUT_SECONDS)
    logger.warning("Failed attempt #%s for %s:%s", attempts, prefix, identifier)
    return attempts


def clear_attempts(prefix, identifier):
    cache.delete(_cache_key(prefix, identifier))