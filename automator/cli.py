import argparse
import sys

from .automator import Automator
from .logger import log, set_logger

def cli(args = sys.argv[0]):
    """Command line interface for the automator. 
    """
    usage = '{} [options]'.format(args)
    description = 'Start the Commensal Automator'
    parser = argparse.ArgumentParser(prog = 'automator', 
                                     usage = usage, 
                                     description = description)
    parser.add_argument('--redis_endpoint', 
                        type = str,
                        default = '127.0.0.1:6379', 
                        help = 'Local Redis endpoint')
    parser.add_argument('--redis_channel',
                        type = str,
                        default = 'alerts', 
                        help = 'Name of the Redis channel to subscribe to')
    if(len(sys.argv[1:]) == 0):
        parser.print_help()
        parser.exit()
    args = parser.parse_args()
    main(redis_endpoint = args.redis_endpoint, 
         redis_channel = args.redis_channel)
    
def main(redis_endpoint, redis_channel):
    """Starts the automator process.
    
    Args:
        redis_endpoint (str): Redis endpoint (of the form 
        <host IP address>:<port>)
        redis_chan (str): Name of Redis channel. 
        
    Returns:
        None    
    """
    set_logger('DEBUG')
    Automation = Automator(redis_endpoint, redis_channel)
    Automation.start()

if(__name__ == '__main__'):
    cli()