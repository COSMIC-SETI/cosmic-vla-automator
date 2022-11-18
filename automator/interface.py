import redis
import logging

class Interface(object):
    """Observing interface class. Provides all automator
    retrieval and command functions.  
    """

    def __init__(self, redis_host, redis_port):
        try:
            self.r = redis.StrictRedis(
                host=redis_host,
                port=redis_port,
                decode_responses=True
            )
        except:
            log.info('Failed to connect to Redis')
    

    def internal_conditions(self):
        """Check if there are any underlying telescope-specific observing 
        conditions set via internal configuration.
        
        Args:
            None 

        Returns:
            True if ANY conditions exist
            False if NO conditions exist 
        """

    def conditionally_observe(self, instances, output_dir):
        """Observe (recording, processing and cleanup) respecting underlying
        telescope-specific low-level observing conditions.

        Args:
            instances (List[str]): List of instances (e.g. [cosmic-gpu-0/0, 
            cosmic-gpu-0/1])
            output_dir (str): File path to recording directory (the same used by 
            each instance)
        
        Returns:
            List of instances for which conditions are met and recording
            initiated. 
        """

    def record(self, instances, duration, rec_dir, rec_type):
        """Instruct instances to record as above, ignoring most 
        conditions.  
        
        Args:
            instances (List[str]): List of instances (e.g. [cosmic-gpu-0/0, 
            cosmic-gpu-0/1])
            duration (float): Recording duration in seconds.
            rec_dir (str): File path to recording directory (may contain
            subdirectories)  
            rec_type (str): Type of recording to be carried out. May be 
            `correlator` or 'voltage`           
        
        Returns:
            List of instances which are recording successfully. 
        """

    def stop_recording(self, instances):
        """Stop any in-progress recording.

        Args:
            instances (List[str]): List of instances (e.g. [cosmic-gpu-0/0, 
            cosmic-gpu-0/1])
        
        Returns:
            List of instances which have stopped recording. 
        """



def cli():
    """CLI for manual command usage.
    """
    import argparse

    # Temporarily elevate logging level to only show errors:
    logger = logging.getLogger()
    logger.setLevel(logging.ERROR)

    parser = argparse.ArgumentParser(
        description="Manually execute Automator-Interface actions.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--redis-host",
        type=str,
        default="redishost",
        help="The redis host.",
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=6973,
        help="The redis host's port.",
    )

    possible_commands = [
        attr
        for attr in dir(Interface)
        if attr.split('_')[0] in ['reflect', 'command']
    ]
    parser.add_argument(
        "command",
        type=str,
        help=(
            "The Automator-Interface method to execute. "
            f"Options are:\n\t{possible_commands}."
        )
    )
    parser.add_argument(
        "command_arguments",
        type=str,
        nargs="*",
        help="The Automator-Interface method's positional arguments.",
    )

    args = parser.parse_args()
    parser

    interface = Interface(
        args.redis_host,
        args.redis_port,
    )

    interface_method = getattr(interface, args.command)
    try:
        interface_method(*args.command_arguments)
    except BaseException as err:
        print(repr(err))


if __name__ == "__main__":
    cli()
