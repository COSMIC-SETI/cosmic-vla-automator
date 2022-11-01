import redis
import json
import sys
import logging
import os

from logger import log
import utils

from cosmic.fengines import ant_remotefeng_map
from cosmic.observations.record import record, hashpipe_recordStop

class Interface(object):
    """Observing interface class. Provides functions to execute
    some basic observing actions. 

    For now, stop-and-stare observing is supported. In future,
    additions will be made to support VLASS-style observing. 

    Offers the following:
        - Retrieval of telescope state
        - Retrieval of F-engine state
        - Retrieval of DAQ states
        - Retrieval of DAQ recording states
        - Retrieval of DATADIR by instance
        - Initiate configuration
        - Initiate recording
        - Initiate processing
        - Initiate post-processing/cleanup functions. 
    """

    def __init__(self):
        self.r = redis.StrictRedis(decode_responses=True)

    def record_fixed(self, duration, project_id='discard'):
        """Instruct instances to record for a fixed RA/Dec
        """
        try:
            log.info('Recording fixed RA, Dec for {} s'.format(duration))
            gateway_keyvals = {'PROJID':'{}'.format(project_id)}
            record(self.r, duration, hashpipe_kv_dict=gateway_keyvals)
        except Exception as e:
            log.info('Recording failed')
            log.info(e)
        return

    def stop_record(self):
        """Stop in-progress recording. 
        """
        try:
            log.info('Stopping recording...')
            hashpipe_recordStop()
        except Exception as e:
            log.info('Could not stop current recording')
            log.info(e)

    def daq_record_modes(self, domain, instances):
        """Determine the current selected recording mode for the specified
        instances. Recording mode key is HPCONFIG. 
        """
        modes = {}
        for instance in instances:
            modes[instance] = utils.hashpipe_key_status(self.r, domain, instance, 'HPCONFIG')
        return modes

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

    def outputdirs(self, domain, instances):
        """Determine the full filepath for the output directories for each 
        instance. 
        Filepath is of the format:
        DATADIR/PROJID/BACKEND
        """
        dirs = {}
        for instance in instances:
            datadir = utils.hashpipe_key_status(self.r, domain, instance, 'DATADIR')
            projid = utils.hashpipe_key_status(self.r, domain, instance, 'PROJID')
            backend = utils.hashpipe_key_status(self.r, domain, instance, 'BACKEND')
            output_path = datadir
            if(projid is not None):
                output_path = os.path.join(output_path, projid)
            if(backend is not None):
                output_path = os.path.join(output_path, backend)
            dirs[instance] = output_path
        return dirs

    def datadirs(self, domain, instances):
        """Determine current DATADIR for all DAQ instances. 
        """
        dirs = {}
        for instance in instances:
            dirs[instance] = utils.hashpipe_key_status(self.r, domain, instance, 'DATADIR')
        return dirs

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
        pktidx = utils.hashpipe_key_status(self.r, domain, instance, 'PKTIDX')
        pktstart = utils.hashpipe_key_status(self.r, domain, instance, 'PKTSTART')
        pktstop = utils.hashpipe_key_status(self.r, domain, instance, 'PKTSTOP')
        
        # ToDo: handle None return values
        # ToDo: pipelining Redis requests

        if pktidx < pktstart:
            # we are set to record when pktidx == pktstart
            return 'armed'
        if pktidx < pktstop and pktstart != 0:
            # we are recording
            return 'recording'
        else:
            # we have completed recording
            return 'idle' 

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

    def src_name(self):
        """Get current source name.
        """
        src_name = utils.hget_decoded(self.r, 'META', 'src')
        if src_name is None:
            return 'unknown'
        else:
            return src_name

def cli(args = sys.argv[0]):
    """CLI for manual command usage.
    """

    # Temporarily elevate logging level to only show errors:
    logger = logging.getLogger()
    logger.setLevel(logging.ERROR)

    interface = Interface()

    if len(sys.argv) < 2:
        print("\nSelect a command from the following:")
        print("\n    record_fixed         Record a fixed RA/Dec. Requires args:")
        print("                             duration:  time to record in seconds")
        print("\n    stop_record          Stop current in-progress recording.")
        print("\n    telescope_state      Current state of the telescope")
        print("\n    fengine_state        Aggregate F-engine state")
        print("\n    expected_antennas    List of antennas which should be active")
        print("\n    daq_states           DAQ statuses. Requires args:")
        print("                             domain:    hashpipe domain")
        print("                             instances: hashpipe instances")
        print("\n    daq_receive_state    Status of DAQ receiving. Requires args:")
        print("                             domain:   hashpipe domain")
        print("                             instance: hashpipe instance")
        print("\n    daq_record_state     Status of DAQ recording. Requires args:")
        print("                             domain:   hashpipe domain")
        print("                             instance: hashpipe instance")
        print("\n    datadirs             Retrieve DATADIR. Requires args:")
        print("                             domain:    hashpipe domain")
        print("                             instances: hashpipe instances")
        print("\n    outputdirs           Location of recorded output data. Requires args:")
        print("                             domain:    hashpipe domain")
        print("                             instances: hashpipe instances")
        print("\n    daq_record_modes     Recording mode for DAQ instances. Requires args:")
        print("                             domain:    hashpipe domain")
        print("                             instances: hashpipe instances")
        print("\n    src_name             Current source name\n")
        return
    
    command = sys.argv[1]
    args = sys.argv[2:]

    if command == 'stop_record':
        interface.stop_record()
        return
    if command == 'record_fixed':
        try:
            duration = int(args[0])
        except:
            print('Bad input (requires integer number of seconds)')
            return
        interface.record_fixed(duration)
        return
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
        instances = args[1:]
        print(interface.daq_states(domain, instances))
        return
    if command == 'daq_receive_state':
        domain = args[0]
        instance = args[1]
        print(interface.daq_receive_state(domain, instance))
        return
    if command == 'daq_record_state':
        domain = args[0]
        instance = args[1]
        print(interface.daq_record_state(domain, instance))
        return
    if command == 'daq_record_modes':
        domain = args[0]
        instances = args[1:]
        print(interface.daq_record_modes(domain, instances))
        return
    if command == 'datadirs':
        domain = args[0]
        instances = args[1:]
        print(interface.datadirs(domain, instances))
        return
    if command == 'outputdirs':
        domain = args[0]
        instances = args[1:]
        print(interface.outputdirs(domain, instances))
        return
    if command == 'src_name':
        print(interface.src_name())
        return
    else:
        print("Command not recognised.")
        return 

if __name__ == "__main__":
    cli()


