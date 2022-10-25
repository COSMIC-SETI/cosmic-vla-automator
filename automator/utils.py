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

