import redis
import json
import sys
import logging
import os

from logger import log
from utils import Utils

from cosmic.fengines import ant_remotefeng_map
from cosmic.observations.record import record, hashpipe_recordStop

from hashpipe_keyvalues.standard import HashpipeKeyValues

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
        self.u = Utils()


    def record_conditional(self, daq_domain, instances, duration, 
                           project_id='discard'):
        """Initiate recording if required conditions are met. 
        """
    
        # Check if F-engines are transmitting packets:
        if len(self.fengine_states()) == 0:
            self.u.alert('No F-engines enabled, therefore not recording.')
            return [] 
    
        # Check DAQ states for each host
        daq_states = self.daq_states(daq_domain, instances)

        if len(daq_states['idle']) == 0:
            self.u.alert('No idle hosts, not initiating new recording.')
            return []

        # Would check here if processing taking place for any instances in the
        # idle list. 

        # Would check here for "wait" conditions
        self.u.alert("Would record now")
        # self.record_fixed(duration, daq_states[idle], project_id) 
        self.u.alerts("Instructed {} to record".format(daq_states[idle]))
        # Return the list of instances that have been instructed to record
        return daq_states[idle]


    def record_fixed(self, duration, instances, project_id='discard'):
        """Instruct instances to record for a fixed RA/Dec
        """
        try:
            log.info('Recording fixed RA, Dec for {} s'.format(duration))
            log.info('Instances: {}'.format(instances))
            # Construct list of gateway interface objects (required by record()):
            # First, separate into pairs, since HashpipeKeyValues requires it:
            host_instances = [instance.split('/') for instance in instances]
            hashpipe_gateway_interfaces = [
                HashpipeKeyValues(host_instance[0], host_instance[1], self.r)
                for host_instance in host_instances
                ]
            # Set specific gateway key-value pairs
            gateway_keyvals = {'PROJID':'{}'.format(project_id)}
            # Record
            #record(self.r, duration, hashpipe_kv_dict=gateway_keyvals)
            self.u.alert("Would record now")
        except Exception as e:
            log.info('Recording failed')
            log.info(e)
        return


    def stop_recording(self):
        """Stop in-progress recording. 
        """
        try:
            self.u.alert('Stopping recording...')
            self.u.alert('[Would stop recording here]')
            #hashpipe_recordStop()
        except Exception as e:
            self.u.alert('Could not stop current recording')
            log.error(e)

    def daq_record_modes(self, domain, instances):
        """Determine the current selected recording mode for the specified
        instances. Recording mode key is HPCONFIG. 
        """
        modes = {}
        for instance in instances:
            modes[instance] = self.u.hashpipe_key_status(self.r, domain, instance, 'HPCONFIG')
        return modes

    def fengine_states(self):
        """Determines the (aggregate) current state of the F-engines.
        """
        # Retrieve F-engine to antenna mapping:
        feng_antenna_map = ant_remotefeng_map.get_antennaFengineDict(self.r)
        # Check F-engine states:
        enabled = []
        for antenna, fengine in feng_antenna_map.items():
            tx_status = fengine.tx_enabled()
            # tx_enabled() returns [1] if transmitting
            if(tx_status[0] == 1):
                enabled.append(antenna)
            else:
                log.warning('F-engine for antenna: {} is not enabled'.format(antenna))
        return enabled

    def outputdirs(self, domain, instances):
        """Determine the full filepath for the output directories for each 
        instance. 
        Filepath is of the format:
        DATADIR/PROJID/BACKEND
        """
        dirs = {}
        for instance in instances:
            datadir = self.u.hashpipe_key_status(self.r, domain, instance, 'DATADIR')
            projid = self.u.hashpipe_key_status(self.r, domain, instance, 'PROJID')
            backend = self.u.hashpipe_key_status(self.r, domain, instance, 'BACKEND')
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
            dirs[instance] = self.u.hashpipe_key_status(self.r, domain, instance, 'DATADIR')
        return dirs


    def daq_states(self, domain, instances):
        """Determine the state of the acquisition pipelines.
        """
        rec_error = []
        idle = []
        armed = []
        recording = []
        unknown = []
        for instance in instances:
            if self.daq_receive_state(domain, instance) > 0:
                rec_error.append(instance)
            else:
                daq_state = self.daq_record_state(domain, instance)
                if daq_state == 'idle':
                    idle.append(instance)
                if daq_state == 'armed':
                    armed.append(instance)
                if daq_state == 'recording':
                    recording.append(instance)
                if daq_state == 'unknown':
                    unknown.append(instance)
        states = {'rec_error':rec_error,
                  'idle':idle,
                  'armed':armed,
                  'recording':recording,
                  'unknown':unknown}
        return states
    

    def daq_receive_state(self, domain, instance):
        """Check that received datarate is close to the expected
        datarate.
        """
        expected_gbps = self.u.hashpipe_key_status(self.r, domain, instance, 'XPCTGBPS')
        actual_gbps = self.u.hashpipe_key_status(self.r, domain, instance, 'IBVGBPS')
        # Needs to be within 0.1% according to Ross
        if abs(expected_gbps - actual_gbps)/expected_gbps < 0.001:
            return 0
        else:
            return 1


    def daq_record_state(self, domain, instance):
        """Determine recording state of a specific DAQ instance.
        """
        pktidx = self.u.hashpipe_key_status(self.r, domain, instance, 'PKTIDX')
        pktstart = self.u.hashpipe_key_status(self.r, domain, instance, 'PKTSTART')
        pktstop = self.u.hashpipe_key_status(self.r, domain, instance, 'PKTSTOP')
        
        # If any of these can't be retrieved, don't trust any of them
        if None in [pktidx, pktstart, pktstop]:
            return 'unknown'

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


    def expected_antennas(self, meta_hash='META', antenna_key='station'):
        """Retrieve the list of antennas that are expected to be used 
        for the current observation.
        """
        antennas = self.u.hget_decoded(self.r, meta_hash, antenna_key)
        # Convert to list:
        if antennas is not None:
            return antennas
        else:
            return []
    

    def on_source_antennas(self, ant_hash='META_flagAnt', on_key='on_source'):
        """Retrieve the list of on-source antennas.
        """
        on_source = self.u.hget_decoded(self.r, ant_hash, on_key)
        if on_source is not None:
            return on_source
        else:
            return []


    def excluded_antennas(self, ant_hash='META_flagAnt', ex_key='excluded'):
        """Retrieve the list of antennas to be excluded from the current 
        observation.
        """
        excluded = self.u.hget_decoded(self.r, ant_hash, ex_key)
        if excluded is not None:
            return excluded
        else:
            return []


    def telescope_state(self, stragglers=0, antenna_hash='META_flagAnt', 
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
            self.u.alert('Telescope unconfigured')
            return 'unconfigured'

    def src_name(self):
        """Get current source name.
        """
        src_name = self.u.hget_decoded(self.r, 'META', 'src')
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
        print("                             instances: list of instances")
        print("\n    stop_record          Stop current in-progress recording.")
        print("\n    telescope_state      Current state of the telescope")
        print("\n    fengine_states       List of antennas with enabled F-engines")
        print("\n    expected_antennas    List of antennas which should be active")
        print("\n    excluded_antennas    List of antennas which should be excluded")
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
        if len(args) < 2:
            print('Missing arguments')
            return
        try:
            duration = int(args[0])
        except:
            print('Bad input (requires integer number of seconds)')
            return
        instances = args[1:]
        interface.record_fixed(duration, instances)
        return
    if command == 'telescope_state':
        print(interface.telescope_state())
        return
    if command == 'fengine_states':
        print(interface.fengine_states())
        return
    if command == 'expected_antennas':
        print(interface.expected_antennas())
        return
    if command == 'excluded_antennas':
        print(interface.excluded_antennas())
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


