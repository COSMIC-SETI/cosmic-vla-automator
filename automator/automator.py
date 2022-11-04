import redis
from interface import Interface
from logger import log

class Automator(object):
    """Automation for commensal observing with the COSMIC system at the VLA.
    This process coordinates and automates commensal observing and SETI 
    search processing at a high level.

    Two observational modes are to be supported: Stop-and-stare (where fixed 
    coordinates in RA and Dec are observed) and VLASS-style observing 
    (scanning across the sky).

    This version is for stop-and-stare observing. 

    Based on the following knowledge:

    - The current state of the telescope
    - The current state of the COSMIC recording/processing system
    - The observing (processing and recording) behaviour desired by operators

    the automator is to determine what instructions (if any) to deliver to the 
    processing nodes. 

    Automator system states (stop and stare):

    - deconfigured (F-engines not transmitting)
    - ready (ready to record)
    - recording  
    - recording_complete (a recording is completed but not processed)
    - processing
    - processing_complete (processing is complete, but postprocessing steps 
      have not taken place)
    - postprocessing

    These are all states at which point a human operator may wish to pause 
    operations. 

    Telescope states (what the telescope is actually doing):

    - deconfigured
    - configured (set of antennas selected for current observation)
    - tracking (antennas are tracking the source)

    F-engine states:

    - enabled (packets are being sent)
    - disabled (packets are not being sent)

    Pipeline states (what the pipeline is actually doing):

    - pipeline-idle (not recording)
    - pipeline-busy (recording)
    - pipeline-error 

    TODO: implement retries for certain operations
    TODO: implement slack notifications for operational stages

    """

    def __init__(self, redis_endpoint, antenna_hash_key):
        """Initialise automator.

        Args:
            redis_endpoint (str): Redis endpoint (of the form 
            <host IP address>:<port>)
        
        Returns:
            None
        """
        log.info('Starting Automator:\n'
                 'Redis endpoint: {}\n'.format(redis_endpoint))
        redis_host, redis_port = redis_endpoint.split(':')
        self.r = redis.StrictRedis(host=redis_host, 
                                              port=redis_port, 
                                              decode_responses=True)
        self.antenna_hash_key = antenna_hash_key

    def start(self):
        """Start the automator. Actions to be taken depend on the incoming 
        observational stage messages on the appropriate Redis channel. 
        """   

        # Wait for telescope to observe something. This is achieved by 
        # checking (each time the META hash is updated, which happens when a new META
        # xml packet is 
        
        # Need slack notifications
        # Need to support wait observations
        # Need to install circus and logging 

        # Subscribe and check for changes to station hash

            # If there's a change, compare station list
                # if on source, check:
                # F-engines TX
                # DAQ receive state
                # DAQ record state

                # wait conditions

                # if unprocessed recordings, 
                # if unpostprocessed recordings

            # If yes, start recording
                # Instruct recording
                # Subscribe and monitor recording state
            
            # When complete:
                # Placeholders for processing

        # Check if we are already on source:
        tel_state_on_startup = Interface.telescope_state(antenna_hash=self.antenna_hash_key)

        if tel_state_on_startup == 'on_source':
            self.propose_recording()                 
        else:
            utils.alert('Telescope in state: {}'.format(tel_state_on_startup))

        # Listen to antenna station key and compare allocated antennas with 
        # on-source antennas to determine recording readiness 
        ps = self.r.pubsub(ignore_subscribe_messages=True)
        ps.subscribe('__keyspace@0__:{}').format(self.antenna_hash_key)
        for key_cmd in ps.listen():
            if(key_cmd['data'] == 'set')

