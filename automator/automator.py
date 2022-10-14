import Redis

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
                 'Redis endpoint: {}\n'
                 'Listening on: {}\n'.format(redis_endpoint, redis_chan)) 
        redis_host, redis_port = redis_endpoint.split(':')
        self.redis_server = redis.StrictRedis(host=redis_host, 
                                              port=redis_port, 
                                              decode_responses=True)
        self.redis_chan = redis_chan


    def start(self, )

    def parse_xml_meta(self, )

    def change_state(self, )

    def waiting(self,)

    def configure(self, )
        
    def record(self, )

    def process(self, )
