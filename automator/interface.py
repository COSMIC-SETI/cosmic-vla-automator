import redis
import json
import sys
import logging

from logger import log
import utils

from cosmic.fengines import ant_remotefeng_map


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

    def fengine_state(self, stragglers=0):
        """Determines the (aggregate) current state of the F-engines.
        """
        # Retrieve F-engine to antenna mapping:
        feng_antenna_map = ant_remotefeng_map.get_antennaFengineDict(self.r)
        # Check F-engine states:
        n_fengines = 0
        n_enabled = 0
        for antenna, fengine in feng_antenna_map.items():
            tx_status = fengine.tx_enabled()
            # tx_enabled() returns [1] if transmitting
            if(tx_status[0] == 1):
                n_fengines += 1
                n_enabled += 1
            else:
                n_fengines += 1
                log.warning('F-engine for antenna: {} is not enabled'.format(antenna))
        if(n_enabled >= n_fengines - stragglers):
            return 'enabled'
        else:
            return 'disabled'

    def daq_states(self, domain, instances):
        """Determine the state of the acquisition pipelines.
        """
        states = {}
        for instance in instances:
            if self.daq_receive_state(domain, instance) > 0:
                states[instance] = 'receive_error'
            else:
                states[instance] = self.daq_record_state(domain, instance)
        return states

    def daq_record_state(self, domain, instance):
        """Determine recording state of a specific DAQ instance.
        """
        state = 'unknown'
        pktidx = utils.hashpipe_key_status(self.r, domain, instance, 'PKTIDX')
        pktstart = utils.hashpipe_key_status(self.r, domain, instance, 'PKTSTART')
        pktstop = utils.hashpipe_key_status(self.r, domain, instance, 'PKTSTOP')
        if pktidx < pktstart:
            # we are set to record when pktidx == pktstart
            state = 'armed'
        elif pktidx >= pktstart:
            if pktidx < pktstop:
                # we are recording
                state = 'recording'
            else:
                # we have completed recording
                state = 'idle' 
        return state

    def daq_receive_state(self, domain, instance):
        """Check that received datarate is close to the expected
        datarate.
        """
        expected_gbps = utils.hashpipe_key_status(self.r, domain, instance, 'XPCTGBPS')
        actual_gbps = utils.hashpipe_key_status(self.r, domain, instance, 'IBVGBPS')
        # Needs to be within 0.1% according to Ross
        if abs(expected_gbps - actual_gbps)/expected_gbps < 0.001:
            return 0
        else:
            return 1

    def expected_antennas(self, meta_hash='META', antenna_key='station'):
        """Retrieve the list of antennas that are expected to be used 
        for the current observation.
        """
        antennas = utils.hget_decoded(self.r, meta_hash, antenna_key)
        # Convert to list:
        if antennas is not None:
            return antennas
        else:
            return []
    
    def on_source_antennas(self, ant_hash='META_flagant', on_key='on_source'):
        """Retrieve the list of on-source antennas.
        """
        on_source = utils.hget_decoded(self.r, ant_hash, on_key)
        if on_source is not None:
            return on_source
        else:
            return []

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

    # Temporarily elevate logging level to only show errors:
    logger = logging.getLogger()
    logger.setLevel(logging.ERROR)

    interface = Interface()

    if len(sys.argv) < 2:
        print("\nSelect a command from the following:")
        print("\n    telescope_state      Current state of the telescope")
        print("\n    fengine_state        Aggregate F-engine state")
        print("\n    expected_antennas    List of antennas which should be active")
        print("\n    daq_states           DAQ statuses. Requires args:")
        print("                             domain:   hashpipe domain")
        print("                             instances: hashpipe instances")
        print("\n    daq_receive_state    Status of DAQ receiving. Requires args:")
        print("                             domain:   hashpipe domain")
        print("                             instance: hashpipe instance")
        print("\n    daq_record_state     Status of DAQ recording. Requires args:")
        print("                             domain:   hashpipe domain")
        print("                             instance: hashpipe instance\n")
        return
    
    command = sys.argv[1]
    args = sys.argv[2:]

    if command == 'telescope_state':
        print(interface.telescope_state())
        return
    if command == 'fengine_state':
        print(interface.fengine_state())
        return
    if command == 'expected_antennas':
        print(interface.expected_antennas())
        return
    if command == 'daq_states':
        domain = args[0]
        instance = args[1:]
        print(interface.daq_states(domain, instance))
        return
    if command == 'daq_receive_state':
        domain = args[0]
        instance = args[1]
        print(interface.daq_receive_state(domain, instance))
        return
    if command == 'daq_record_state':
        domain = args[0]
        instances = args[1]
        print(interface.daq_record_state(domain, instances))
        return

    else:
        print("Command not recognised.")
        return 

if __name__ == "__main__":
    cli()


