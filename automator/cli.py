import argparse
import sys

from automator import Automator
from logger import log, set_logger

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
    parser.add_argument('--antenna_key', 
                        type = str,
                        default = 'META_flagAnt', 
                        help = 'Antenna flag key.')
    parser.add_argument('--daq_domain', 
                        type = str,
                        default = 'hashpipe', 
                        help = 'DAQ domain')
    parser.add_argument('--duration', 
                        type = str,
                        default = '60', 
                        help = 'Recording duration, in seconds')
    parser.add_argument('--instances',
                        nargs='*',
                        action='store',
                        default = None,
                        help = 'Available instances')
    if(len(sys.argv[1:]) == 0):
        parser.print_help()
        parser.exit()
    args = parser.parse_args()
    main(redis_endpoint = args.redis_endpoint, 
         antenna_key = args.antenna_key,
         daq_domain = args.daq_domain,
         duration = args.duration,
         instances = args.instances
         )

    
def main(redis_endpoint, antenna_key, daq_domain, duration, instances):
    """Starts the automator process.
    
    Args:
        redis_endpoint (str): Redis endpoint (of the form 
        <host IP address>:<port>)
        redis_chan (str): Name of Redis channel. 
        
    Returns:
        None    
    """
    set_logger('DEBUG')
    Automation = Automator(redis_endpoint, 
                           antenna_key, 
                           instances, 
                           daq_domain, 
                           duration)
    Automation.start()

if(__name__ == '__main__'):
    cli()