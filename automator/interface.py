# import redis
import sys
import logging

# from logger import log
# from utils import Utils


class Interface(object):
    """Observing interface class. Provides the functions
    that constitute the automator.

    Offers the following:
        - Command an query of what observations are possible, now
        - Reflect what the telescope can observe
        - Command an observation
        - Reflect an observation
    """

    def __init__(self, redis_host, redis_port):
        self.r = None
        # self.r = redis.StrictRedis(
        #     host=redis_host,
        #     port=redis_port,
        #     decode_responses=True
        # )

    def command_observation_possible(self):
        self.r.hset("observations_possible", "COMMAND", "QUERY")

    def reflect_observation_possible(self):
        value = self.r.hget("observations_possible", "STATUS")
        if value == "None":
            return None
        return value

    def command_observation(self, possible_observation):
        self.r.hset("observation", "COMMAND", possible_observation)

    def reflect_observation(self):
        return self.r.hget("observation", "STATUS")


def cli():
    """CLI for manual command usage.
    """
    import argparse

    # Temporarily elevate logging level to only show errors:
    logger = logging.getLogger()
    logger.setLevel(logging.ERROR)

    parser = argparse.ArgumentParser(
        description="Manually execute Automator-Interface actions.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter  # set the thing so defaults are displayed in the usage printout
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

    possible_commands = [attr for attr in dir(Interface) if attr.split('_')[0] in ['reflect', 'command']]
    parser.add_argument(
        "command",
        type=str,
        help=f"The Automator-Interface method to execute. Options are:\n\t{possible_commands}.",
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


