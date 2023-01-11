import redis
import logging
import inspect

from logger import log
from utils import Utils

from cosmic.observations.record import record as cosmic_record, hashpipe_recordStop
from cosmic.hashpipe_aux import HashpipeKeyValues


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
        try:
            self.redis_obj = redis.StrictRedis(
                host=redis_host,
                port=redis_port,
                decode_responses=True
            )
            self.redis_pubsub = self.redis_obj.pubsub(ignore_subscribe_messages=True)
        except:
            log.info('Failed to connect to Redis')


    def _execute_with_response_in_key(self,
        func,
        redis_key,
        message_limit: int = 5,
        get_message_timeout: float = 0.5,
    ):
        """
        Execute a given function enclosed in a subscription to the keyspace
        of a redis_key.

        Params
        ------
        func: Callable(**kwargs)
            The function to execute, is given the kwarg `redis_obj=self.redis_obj`
        redis_key: str
            The redis-key that is subscribed to before `func` is executed, 
        message_limit: int = 5
            The maximum number of messages to consider before raising a RuntimeError.
            This includes a lack of a message due to a timeout.
        get_message_timeout: float = 0.5
            The duration after which each iterated `get_message` should timeout.
        
        Return
        ------
        str: the value of the redis_key (`self.redis_obj.get(redis_key)`)
        """
        channel = f"__keyspace@0__:{redis_key}"
        self.redis_pubsub.subscribe(channel)
        func(redis_obj=self.redis_obj)
        while message_limit > 0:
            message = self.redis_pubsub.get_message(timeout=get_message_timeout)
            message_limit -= 1
            if all(
                message is not None,
                message['type'] == 'message',
                message['channel'] == channel,
                message['data'] == 'set',
            ):
                break
        self.redis_pubsub.unsubscribe(channel)
        if message_limit <= 0:
            raise RuntimeError(f"Message limit reached while waiting for a response on {channel}: {message_limit} * {get_message_timeout} seconds.")
        return self.redis_obj.get(redis_key)


    def internal_conditions(self):
        """Check if there are any underlying telescope-specific observing 
        conditions set via internal configuration.
        
        Args:
            None 

        Returns:
            True if ANY conditions exist
            False if NO conditions exist 
        """

        response = self._execute_with_response_in_key(
            lambda **kwargs: kwargs["redis_obj"].set("observationQuery", "?"),
            "observationPossibilities"
        )

        return int(response) > 0

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
        
        response = self._execute_with_response_in_key(
            lambda **kwargs: kwargs["redis_obj"].set("observationExecute", "!"),
            "observationExecutingOn"
        )
        return response.split(';')

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
        hashipe_targets = [
            HashpipeKeyValues(*instance.split('/'), self.redis_obj)
            for instance in instances
        ]
        cosmic_record(
            self.redis_obj,
            duration,
            hashpipe_kv_dict = {
                'PROJID': rec_dir
            },
            hashpipe_targets = hashpipe_targets,
            delay_seconds = 3
        )
        return instances

    def stop_recording(self, instances):
        """Stop any in-progress recording.

        Args:
            instances (List[str]): List of instances (e.g. [cosmic-gpu-0/0, 
            cosmic-gpu-0/1])
        
        Returns:
            List of instances which have stopped recording. 
        """
        hashpipe_recordStop(
            [
                HashpipeKeyValues(*instance.split('/'), self.redis_obj)
                for instance in instances
            ]
        )
        return instances

    def is_vlass_obs(self):
        """Check if current observation is a VLASS observation. 
        """
        # VLASS project IDs are TSKY0001 or VLASS*
        intents = self.u.hget_decoded(self.r, 'META', 'intents')
        projid = intents['ProjectID']
        if projid == 'TSKY0001' or 'VLASS' in projid:
            return True
        else:
            return False

    def is_vlass_cal(self):
        """Check if current observation is a VLASS calibration observation of
        a fixed RA/Dec.
        """
        # VLASS project IDs are TSKY0001 or VLASS*
        intents = self.u.hget_decoded(self.r, 'META', 'intents')
        scan_intent = intents['ScanIntent']
        if 'CALIBRATE' in scan_intent:
            return True
        else:
            return False

    def is_vlass_track(self):
        """Check if current observation is a VLASS track.
        """
        # VLASS project IDs are TSKY0001 or VLASS*
        intents = self.u.hget_decoded(self.r, 'META', 'intents')
        scan_intent = intents['ScanIntent']
        if scan_intent == 'OBSERVE_TARGET':
            return True
        else:
            return False

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

    command_paramters_map = {
        attr: [
            f"{param}" + (" *REQUIRED*" if param.default == inspect.Parameter.empty else f"={param.default}")
            for key, param in inspect.signature(getattr(Interface, attr)).parameters.items()
            if key != "self"
        ]
        for attr in dir(Interface)
        if attr.split('_')[0] in ['reflect', 'command']
    }
    parser.add_argument(
        "command",
        type=str,
        help=(
            "The Automator-Interface method to execute. "
            f"Options are:\n\t{list(command_paramters_map.keys())}."
        )
    )
    parser.add_argument(
        "command_arguments",
        type=str,
        nargs="*",
        default=[],
        help="The Automator-Interface method's positional arguments.",
    )

    args = parser.parse_args()

    interface = Interface(
        args.redis_host,
        args.redis_port,
    )

    interface_method = getattr(interface, args.command)
    if any(help_arg in args.command_arguments for help_arg in ['-h', '--help']):
        print(f"Signature: {args.command}({','.join(command_paramters_map[args.command])})")
    else:
        try:
            interface_method(*args.command_arguments)
        except BaseException as err:
            print(repr(err))
            print()
            print(f"Signature: {args.command}({','.join(command_paramters_map[args.command])})")


if __name__ == "__main__":
    cli()
