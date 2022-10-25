"""Utilities for reuse across automator. 
"""

import json
import redis

from logger import log

def hget_decoded(r, r_hash, r_key):
    """Fetch a single redis key from a hash.
    """
    # Retrieve hash value for r_key:
    val = r.hget(r_hash, r_key)
    # Deserialise:
    if val is not None: # key exists
        val = json.loads(val)
    return val

def hashpipe_key_status(r, domain, host, instance, key, group=None):
    """Retrieve the value of a hashpipe-redis gateway status key.
    """
    if group == None:
        status_hash = '{}://{}/{}/status'.format(domain, host, instance)
    else:
        status_hash = '{}:{}//{}/{}/status'.format(domain, group, host, instance)
    log.info(status_hash)
    value = hget_decoded(r, status_hash, key)
    return value