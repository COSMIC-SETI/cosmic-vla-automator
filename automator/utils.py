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
        try:
            val = json.loads(val)
        except json.decoder.JSONDecodeError:
            log.warning('Could not decode: {}'.format(val))
            log.warning('Returning as a string.')
    return val

def hashpipe_key_status(r, domain, instance, key, group=None):
    """Retrieve the value of a hashpipe-redis gateway status key.
    Instance should be of the form: <host>/<instance number>
    """
    if group == None:
        status_hash = '{}://{}/status'.format(domain, instance)
    else:
        status_hash = '{}:{}//{}/status'.format(domain, group, instance)
    val = hget_decoded(r, status_hash, key)
    return val