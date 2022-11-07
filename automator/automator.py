import redis

from interface import Interface
from logger import log
from utils import Utils

class Automator(object):
    """Automation for commensal observing with the COSMIC system at the VLA.
    This process coordinates and automates commensal observing and SETI 
    search processing at a high level.

    Two observational modes are to be supported: Stop-and-stare (where fixed 
    coordinates in RA and Dec are observed) and VLASS-style observing 
    (scanning across the sky).

    Based on the following knowledge:

    - The current state of the telescope
    - The current state of the COSMIC recording/processing system
    - The observing (processing and recording) behaviour desired by operators

    the automator is to determine what instructions (if any) to deliver to the 
    processing nodes. 

    TODO: implement retries for certain operations
    TODO: implement slack notifications for operational stages
    """

    def __init__(self, redis_endpoint, antenna_key, instances, daq_domain, 
                 duration):
        """Initialise automator.

        Args:
            redis_endpoint (str): Redis endpoint (of the form 
            <host IP address>:<port>)
        
        Returns:
            None
        """
        redis_host, redis_port = redis_endpoint.split(':')
        # Redis connection:
        self.r = redis.StrictRedis(host=redis_host, 
                                              port=redis_port, 
                                              decode_responses=True)
        # Utilities:
        self.u = Utils()
        # Interface:
        self.interface = Interface()
        self.antenna_hash_key = antenna_key
        self.instances = instances
        self.daq_domain = daq_domain
        self.duration = duration
        self.telescope_state = 'unknown'


    def start(self):
        """Start the automator. Actions to be taken depend on the incoming 
        observational stage messages on the appropriate Redis channel. 
        """   
        
        self.u.alert('Starting up...')
        ps = self.r.pubsub(ignore_subscribe_messages=True)
        telescope_on_startup = self.interface.telescope_state(
            antenna_hash=self.antenna_hash_key
            )
        self.u.alert('Telescope on startup: {}'.format(telescope_on_startup))
        self.telescope_state = telescope_on_startup
        if telescope_on_startup == 'on_source':
            self.telescope_on_source(self, ps)

        # Listen to antenna station key to compare allocated antennas with 
        # on-source antennas to determine recording readiness 
        self.u.alert('Listening to telescope state...')
        ps.subscribe('__keyspace@0__:{}'.format(self.antenna_hash_key))

        # Check incoming messages. 
        for updated_key in ps.listen():
            if updated_key['data'] == 'hset':
                # Check which hash was updated (note, we can only detect if
                # entire hash was updated)
                channel = updated_key['channel'].split(':', 1)[1]
                
                # If the antenna flags have been updated, check if the telescope 
                # has transitioned between off_source and on source:
                if channel == self.antenna_hash_key:
                    self.telescope_state_change(ps)

                # If this is a recording update:
                else:
                    self.recording_state_change(ps, channel)


    def recording_state_change(self, ps, channel):
        """Actions to take if recording state changes.
        """
        instance = self.parse_instance(channel)
        if instance is not None:
            # Get new recording state:
            new_state = self.u.daq_record_state(self.daq_domain, instance)
            if new_state == 'idle':
                # Transition to idle
                # Unsubscribe from any recording keyspace notifications
                self.unsubscribe_instances(self.daq_domain, [instance], ps)

                self.u.alert('Would initiate processing: {}'.format(instance))
            else:
                self.u.alert('{}: new state: {}'.format(instance, new_state))


    def parse_instance(self, channel):
        """Given a keyspace channel name for a possible instance, retrieve
        the potential instance name and check if it is on the list of 
        available instances. 
        """
        try:
            instance = channel.split('{}://', 1)[1]
            instance = instance.split('/status')[0]
            if instance in self.instances:
                return instance
            self.u.alert('Instance not in local instance list')
            return 
        except:
            self.u.alert('Could not parse pubsub message: {}'.format(channel))
            return


    def telescope_state_change(self, ps):
        """Actions to take if telescope state changes.
        """
        # Retrieve new telescope state:
        telescope_state = self.interface.telescope_state(
            antenna_hash=self.antenna_hash_key
            )
        # Return if telescope state has not changed from prior state
        if telescope_state == self.telescope_state:
            return
        self.telescope_state = telescope_state
        # Stop recording for all instances if telescope moves off 
        # source during recording:
        if telescope_state == 'off_source':
            self.telescope_off_source(ps)
        # Potentially start recording if the telescope moves on source:
        elif telescope_state == 'on_source':
            self.telescope_on_source(ps)


    def telescope_off_source(self, ps):
        """If the telescope moves off source, the following actions are taken.
        """
        daq_states = self.interface.daq_states(self.daq_domain, self.instances)
        recording = daq_states['recording']
        if len(recording) > 0:
            self.interface.stop_recording()
            # Unsubscribe from any recording keyspace notifications
            self.unsubscribe_instances(self.daq_domain, recording, ps)
            # Potentially start processing here:
            self.u.alert('Processing would begin for: {}'.format(recording))


    def telescope_on_source(self, ps):
        """If the telescope moves on source, the following actions
        are taken. 
        """
        # If we are on source, potentially initiate recording for any 
        # available processing nodes 
        rec_instances = self.interface.record_conditional(
            self.daq_domain,
            self.instances,
            self.duration
            )
        if len(rec_instances) > 0:
            # Subscribe to hashpipe instance hashes to monitor recording:
            self.subscribe_instances(self.daq_domain, rec_instances, ps)


    def subscribe_instances(self, domain, instances, ps):
        """Subscribe to monitor each instance's gateway hash.
        """
        for instance in instances:
           instance_channel = '{}://{}/status'.format(domain, instance)
           ps.subscribe('__keyspace@0__:{}'.format(instance_channel))


    def unsubscribe_instances(self, domain, instances, ps):
        """Unsubscribe from an instance's gateway hash.
        """
        for instance in instances:
            instance_channel = '{}://{}/status'.format(domain, instance)
            ps.unsubscribe('__keyspace@0__:{}'.format(instance_channel))




