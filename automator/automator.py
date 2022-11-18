import redis

from interface import Interface
from logger import log
from utils import Utils

class Automator(object):
    """Automation for observations.
    This process coordinates the initiation of observations with
    observations possible. See `interface.py` for the atomic actions
    that enable this.

    """

    def __init__(self, redis_endpoint):
        """Construct an Automator.

        Args:
            redis_endpoint (str): Redis endpoint (of the form
            <host IP address>:<port>)
        """
        redis_host, redis_port = redis_endpoint.split(':')
        # Redis connection:
        self.r = redis.StrictRedis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        # Utilities:
        self.u = Utils()
        # Interface:
        self.interface = Interface(
            redis_host,
            redis_port
        )

        self.hash_callback_map = {
            "observations_possible": self.telescope_state_change,
            "observation": self.recording_state_change
        }

    def start(self):
        """Start the automator. Actions to be taken depend on the incoming
        observational stage messages on the appropriate Redis channel.
        """

        self.u.alert('Starting up...')
        ps = self.r.pubsub(ignore_subscribe_messages=True)

        # Listen to antenna station key to compare allocated antennas with
        # on-source antennas to determine recording readiness
        self.u.alert('Listening to telescope state...')
        for hashname in self.hash_callback_map.keys():
            ps.subscribe(f'__keyspace@0__:{hashname}')

        # Get the ball rolling
        self.interface.command_observation_possible(
            self.hashname_obspossible
        )

        # Check incoming messages.
        for updated_key in ps.listen():
            if updated_key['data'] == 'hset':
                # Check which hash was updated (note, we can only detect if
                # entire hash was updated)
                hashname = updated_key['channel'].split(':', 1)[1]

                if hashname in self.hash_callback_map:
                    self.hash_callback_map[hashname]()


    def telescope_state_change(self):
        """Actions to take if telescope state changes.
        """

        # Retrieve response:
        observation_possible = self.interface.reflect_observation_possible()
        if observation_possible is None:
            self.interface.command_observation_possible()
        else:
            self.interface.command_observation(
                observation_possible
            )


    def recording_state_change(self):
        """Actions to take if recording state changes.

        """
        observation_state = self.interface.reflect_observation()
        if observation_state == "Pending":
            return

        if observation_state == "Succeeded":
            self.u.alert("Observation completed.")
        elif observation_state == "Failed":
            self.u.alert("Observation failed!")
        else:
            raise ValueError(
                "`reflect_observation` Interface-method returned unrecognised "
                f"value: {observation_state}"
            )

        # Previous completed, restart the cycle
        self.interface.command_observation_possible()
