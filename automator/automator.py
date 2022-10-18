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

    Automator system states (stop and stare):

    - deconfigured
    - configured
    - recording
    - recording_complete
    - processing
    - processing_complete
    - postprocessing

    These are all states at which point a human operator may wish to pause 
    operations. 

    Telescope states (what the telescope is actually doing):

    - deconfigured
    - configured
    - tracking

    Pipeline states (what the pipeline is actually doing):

    - pipeline-idle (not recording)
    - pipeline-busy (recording)
    - pipeline-error 

    TODO: implement retries for certain operations
    TODO: implement slack notifications for operational stages

    """

    def __init__(self, redis_endpoint, telescope_status_key, pipeline_status_key, control_key):
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
        self.telescope_status_key = telescope_status_key
        self.pipeline_status_key = pipeline_status_key
        self.control_key = control_key # Set this key to manually control operations
        self.system_state = 'deconfigure'
        self.telescope_state = self.redis_server.get(telescope_status_key)
        self.pipeline_state = self.redis_server.get(pipeline_status_key)
        self.control = self.redis_server.get(control_key)

    def start(self):
        """Start the automator. Actions to be taken depend on the incoming 
        observational stage messages on the appropriate Redis channel. 
        """    
        ps = self.redis_server.pubsub(ignore_subscribe_messages=True)
        ps.subscribe('__keyspace@0__:{}').format(self.telescope_status_key)
        ps.subscribe('__keyspace@0__:{}').format(self.pipeline_status_key)
        ps.subscribe('__keyspace@0__:{}').format(self.control_key)
        log.info('Listening to telescope status key: {}'.format(self.telescope_status_key)) 
        log.info('Listening to pipeline status key: {}'.format(self.pipeline_status_key)) 
        log.info('Listening to control key: {}'.format(self.control_key)) 
        for key_cmd in ps.listen():
            if(key_cmd['data'] == 'set'):
                status_key = key_cmd['channel'].split(':')[1]
                val = self.redis_server.get(status_key)    
                if(status_key == self.telescope_status_key):
                    log.info("New telescope state: {}".format(val)) 
                    self.telescope_state = val
                    self._update(key_val)
                if(status_key == self.pipeline_status_key): 
                    log.info("New pipeline state: {}".format(val)) 
                    self.pipeline_state = val
                    self._update(key_val)
                if(status_key == self.control_key): 
                    log.info("Control updated: {}".format(val)) 
                    self.control = val
    
    def _update(self, new_state):
        """Determine what to do (if anything) in response to a change 
        in telescope state or pipeline state.
        """
        if(self.control == 'pause'):
            log.info('All operations currently paused')
            log.info('Ignoring new state: {}'.format(new_state))
        else:
            log.info("New state: {}".format(new_state)) 
            states = {'configured':self._configure,
                      'tracking':self._tracking,
                      'deconfigured':self._deconfigure,
                      'pipeline-idle':self._pipeline_idle,
                      'pipeline-error':self._pipeline_error}       
        return states.get(new_state, self._ignored_state)

    def _configure(self):
        """The telescope is configured, but not tracking a source.
        """       
        if(self.system_state == 'tracking'):
            result = Interface.stop_recording()
            if(result == 0):
                self.system_state = 'recording_complete'
                log.info("Recording stopped, proceeding to processing")
                self._process()
        elif(self.system_state == 'deconfigured'):
            result = Interface.configure()
            if(result == 0):
                self.system_state = 'configured'
                log.info("System configured")
        else:
            log.info("System in state {}; ignoring telescope state {}".format(self.system_state, self.telescope_state))

    def _tracking(self):
        """If appropriate, the automator will instruct backend processes to record. 
        """

        if(self.system_state == 'deconfigured'):
            log.info('Telescope is tracking, but the system is not configured')
            log.info('Attempting configuration')
            result = Interface.configure()
            if(result == 0):
                self.system_state = 'configured'
                log.info('System configured')

        if((self.system_state == 'configured') & (self.pipeline_state == 'pipeline-idle')):
            log.info('Initiating recording')
            # note: Interface.record() should return when recording
            # has started successfully. 
            result = Interface.record()
            if(result == 0):
                self.system_state = 'record'
                log.info('System recording')

        else:
            log.info('Telescope is tracking, but system state is {} and pipeline state is {}'.format(self.system_state, self.pipeline_state))      
            log.info('Not recording')
                
    def _pipeline_error(self):
        """If something goes wrong with recording.
        """
        if(self.system_state == 'recording'):
            self.system_state = 'configured'
            log.error('Recording error; returning system to configured state')

    def _pipeline_idle(self):
        """If pipeline transitions into idle state (task was successful).
        """
        if(self.system_state == 'recording'):
            self.system_state = 'recording_complete'
            log.info('Recording completed, proceeding to processing')
            self._process()
        
    def _process(self):
        """The automator will instruct the COSMIC backend systems to process. 
        """
        if(self.system_state == 'recording_complete'):
            result = Interface.process()
            if(result == 0):
                self.system_state = 'processing_complete'
                log.info('Processing completed, proceeding to postprocessing')
                self._postprocessing()
        else:
            "Not processing; telescope state: {}, system state {}".format(self.telescope_state, self.system_state)

    def _postprocessing(self):
        """Postprocessing initiated here.
        """
        if(self.system_state == 'processing_complete'):
            result = Interface.postprocess()
            if(result == 0):
                self.system_state = 'configured'
                log.info('Postprocessing completed, returning to system state: configured')
        else:
            "Not postprocessing; telescope state: {}, system state {}".format(self.telescope_state, self.system_state)

