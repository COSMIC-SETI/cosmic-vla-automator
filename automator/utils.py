import json
import redis
import os
from datetime import datetime

from logger import log

# Temporary local slackbot class:
from slackbot import SlackBot

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
        print(message)
        slack_message = '{} automator: {}'.format(self.timestamp(), message)
        self.slackproxy.post_message(slack_message)
