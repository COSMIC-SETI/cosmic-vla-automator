import Redis

from .interface import Interface
from .logger import log

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

    System states (stop and stare):

    - deconfigured
    - configured
    - recording
    - processing
    - postprocessing

    Telescope states (stop and stare):

    - deconfigured
    - configured
    - tracking

    """

    def __init__(self, redis_endpoint, status_key):
        """Initialise automator.

        Args:
            redis_endpoint (str): Redis endpoint (of the form 
            <host IP address>:<port>)
            redis_chan (str): Name of Redis channel. 
        
        Returns:
            None
        """
        log.info('Starting Automator:\n'
                 'Redis endpoint: {}\n'.format(redis_endpoint))
        redis_host, redis_port = redis_endpoint.split(':')
        self.redis_server = redis.StrictRedis(host=redis_host, 
                                              port=redis_port, 
                                              decode_responses=True)
        self.status_key = status_key
        self.system_state = 'deconfigure'
        self.telescope_state = 'unknown'

    def start(self):
        """Start the automator. Actions to be taken depend on the incoming 
        observational stage messages on the appropriate Redis channel. 
        """    
        ps = self.redis_server.pubsub(ignore_subscribe_messages=True)
        ps.subscribe('__keyspace@0__:{}').format(self.status_key)
        log.info('Listening to status key: {}'.format(self.status_key)) 
        for key_cmd in ps.listen():
            if(key_cmd['data'] == 'set'):
                telescope_status = self.redis_server.get(self.status_key)     
                self._update(telescope_status)
    
    def _update(self, telescope_status):
        """Determine what to do (if anything) in response to a change 
        in telescope state.
        """
        log.info("New telescope state: {}".format(telescope_status)) 
        states = {'configured':self._configure,
                  'tracking':self._tracking,
                  'deconfigured':self._deconfigure}       
        return states.get(telescope_status, self._ignored_state)

    def _configure(self):
        """The telescope is configured, but not tracking a source.
        """       
        self.telescope_state = 'configured'
        if(self.system_state == 'tracking'):
            result = Interface.stop_recording()
            if(result == 0):
                self.system_state = 'configured'
        elif(self.system_state == 'deconfigured'):
            result = Interface.configure()
            if(result == 0):
                self.system_state = 'configured'
        else:
            log.info("System in state {}; ignoring telescope state {}".format(self.system_state, self.telescope_state))

    def _configure(self):
        """The automator will request that the COSMIC backend systems prepare
        for recording.
        """
        if(self.state is not 'idle'):
            log.info("Not in idle state, therefore not configuring.")
            return
        self.state = 'configuring'
        result = Interface.configure()
        if(result == 0):
            self.state = 'configured'
            log.info("The automator is in state CONFIGURED.")
            # Will publish a message to slack here
        else:
            log.info("Configuration failed. Returning to state IDLE")
            self.state = 'idle'

    def _record(self):
        """The automator will instruct the COSMIC backend systems to record. 
        """
        if(self.state is not 'configured'):
            log.info("Not ready for new recording.")
            return
        self.state = 'recording'
        log.info("The automator is in state RECORD.")
        result = Interface.record()
        if(result == 0):
            log.info("Recording successful.")
            self.state = 'recorded'
            self._process()
        else:
            log.info("Recording failed. Returning to state CONFIGURED.")
            self.state = 'configured'
        
    def _process(self):
        """The automator will instruct the COSMIC backend systems to process. 
        """
        if(self.state is not 'recorded'):
            log.info("Not ready to process.")
            return
        self.state = 'processing'
        log.info("The automator is in state PROCESSING")
        result = Interface.process()
        if(result == 0):
            log.info("Processing successful.")
            self.state = 'processed'
            self._cleanup()
        else:
            log.info("Processing failed. Returning to state RECORDED.")
            self.state = 'recorded'
            # Will implement horrid recursive retries here

    def _cleanup(self):
        """The automator will instruct the COSMIC backend systems to perform
        any required cleanup operations (e.g. emptying the NVMe modules). 
        """
        if(self.state is not 'processed'):
            log.info("Not ready for cleanup.")
            return
        self.state = 'cleaning'
        log.info("The automator is in state CLEANING")
        result = Interface.cleanup()
        if(result == 0):
            log.info("Cleanup successful. Returning to state CONFIGURED")
            self.state = 'configured'
        else:
            log.info("Cleanup failed. Returning to state PROCESSED.")
            self.state = 'processed'
            # Will implement recursive retries here

