import json
import redis
import os
import time

from datetime import datetime

from logger import log

# Temporary local slackbot class:
from slackbot import SlackBot
# from cosmic.observations.slackbot import SlackBot

SLACK_ENV_VAR = "AUTOMATOR_SLACK_TOKEN"
SLACK_CHANNEL = "cosmic-vla-automator"
SLACK_CHANNEL_ID = "C04ADDB931N"

class Utils(object):
    """Utilities for reuse across automator. 
    """

    def __init__(self):
        token = os.environ[SLACK_ENV_VAR]
        self.slackproxy = SlackBot(token, SLACK_CHANNEL, SLACK_CHANNEL_ID)

    def hget_decoded(self, r, r_hash, r_key):
        """Fetch a single redis key from a hash.
        """
        # Check if key actually exists
        if r.exists(r_hash):
            # Retrieve hash value for r_key:
            val = r.hget(r_hash, r_key)
            # Try to deserialise:
            try:
                val = json.loads(val)
            except json.decoder.JSONDecodeError:
                log.warning('Could not decode: {}'.format(val))
                log.warning('Returning as a string.')
            except TypeError:
                log.warning('Cannot decode NoneType.')
            return val
        else:
            self.alert('Hash {} does not exist'.format(r_hash))
            return
    
    def hashpipe_key_status(self, r, domain, instance, key, group=None):
        """Retrieve the value of a hashpipe-redis gateway status key.
        Instance should be of the form: <host>/<instance number>
        """
        if group == None:
            status_hash = '{}://{}/status'.format(domain, instance)
        else:
            status_hash = '{}:{}//{}/status'.format(domain, group, instance)
        val = self.hget_decoded(r, status_hash, key)
        return val

    def pooled_status(self, r, hash_name):
        """Return pooled status lists
        """
        instance_list = r.hkeys(hash_name)
        active_instances = 0
        status_types = {}
        for instance in instance_list:
            status = self.hget_decoded(r, hash_name, instance)
            # If status is None ('null' in redis), assume instance is offline.
            if status is None:
                continue
            if not status in status_types:
                status_types[status] = [instance]
                active_instances += 1
            else:
                status_types[status].append(instance)
                active_instances += 1
        return status_types, active_instances

    def timestamp(self):
        """Report UTC timestamp for slack alerts in ISO format.
        """
        now = datetime.utcnow().isoformat(timespec='milliseconds')
        ts = '[{}Z]'.format(now)
        return ts

    def alert(self, message):
        """Alert via Slack and log message.
        """
        log.info(message)
        slack_message = '{} automator: {}'.format(self.timestamp(), message)
        self.slackproxy.post_message(slack_message)
