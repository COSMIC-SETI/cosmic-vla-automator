import redis
import json
import sys

class Interface(object):
    """Observing interface class. Provides functions to execute
    some basic observing actions. 

    For now, stop-and-stare observing is supported. In future,
    additions will be made to support VLASS-style observing. 

    Offers the following:
        - Retrieval of telescope state
        - Initiate configuration
        - Initiate recording
        - Initiate processing
        - Initiate post-processing/cleanup functions. 
    """

    def __init__(self):
        self.r = redis.StrictRedis(decode_responses=True)

    def expected_antennas(self, meta_hash='META', antenna_key='station'):
        """Retrieve the list of antennas that are expected to be used 
        for the current observation.
        """
        # Stringified list of antennas:
        antenna_str = self.r.hget(meta_hash, antenna_key)
        # Convert to list:
        if antenna_str is not None:
            antenna_list = json.loads(antenna_str)
        else:
            antenna_list = []
        return antenna_list 
    
    def on_source_antennas(self, ant_hash='META_flagant', on_key='on_source'):
        """Retrieve the list of on-source antennas.
        """
        on_source_str = self.r.hget(ant_hash, on_key)
        if on_source_str is not None:
            on_source = json.loads(on_source_str)
        else:
            on_source = []
        return on_source

    def telescope_state(self, stragglers=0, antenna_hash='META_flagant', 
        on_key='on_source'):
        """Retrieve the current state of the telescope. This must be 
        achieved by looking at which antennas are actually observing
        as expected. 

        States include:
            unconfigured: no antennas assigned to an observation
            on_source: on source antennas >= off source antennas - stragglers
            off_source: on source antennas < off source antennas - stragglers

        Args:
            stragglers (int): number of off-source stragglers permitted
            when considering the telescope to be on source.  
            antenna_hash (str): hash containing antenna status lists.
            on_key (str): key for the list of on-source antennas. 

        Returns: 
            state (str): telescope state. 
        """ 
        # Max list of antennas expected 
        antennas = self.expected_antennas()
        if len(antennas) > 0:
            # Retrieve on source antennas:
            on_source = self.on_source_antennas()
            if len(on_source) >= (len(antennas) - stragglers):
                return 'on_source'
            else:
                return 'off_source'
        else:
            return 'unconfigured'


def cli(args = sys.argv[0]):
    """CLI for manual command usage.
    """

    interface = Interface()

    if len(sys.argv) < 2:
        print("\nSelect a command from the following:\n")
        print("telescope_state    current state of the telescope")
        return
    
    command = sys.argv[1]
    args = sys.argv[2:]

    if command == 'telescope_state':
        print(interface.telescope_state())
        return

    else:
        print("Command not recognised.")
        return 

if __name__ == "__main__":
    cli()


