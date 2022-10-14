import Redis

from .interface import Interface
from .logger import log

class Automator(object):
    """Automation for commensal observing with the COSMIC system at the VLA.
    This process coordinates and automates commensal observing and SETI 
    search processing at a high level.

    Two observational modes are supported: Stop-and-stare (where fixed 
    coordinates in RA and Dec are observed) and VLASS-style observing 
    (scanning across the sky).


    """

    def __init__(self, redis_endpoint, redis_chan):
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
        self.redis_chan = redis_chan
        self.state = 'idle'

    def start(self):
        """Start the automator. Actions to be taken depend on the incoming 
        observational stage messages on the appropriate Redis channel. 
        """             
        ps = self.redis_server.pubsub(ignore_subscribe_messages=True)
        ps.subscribe(self.redis_chan)
        log.info('Listening on: {}\n'.format(redis_chan)) 
        for msg in ps.listen():
            self.parse_xml_meta(msg)

    def _parse_xml_meta(self, ):
        """Parses the incoming metadata and does the following:

        1. Determines telescope observing state
        2. Changes the automator state in response
        3. Retrieves and transmits any metadata if necessary
        """

    def _idle(self):
        """Idle state: Neither the telescope itself nor COSMIC are doing
        anything. 
        """       
        log.info("The automator is now IDLE")
        # Will publish a message to slack here

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

