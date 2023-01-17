import redis
import logging
import inspect
import json

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
            self.r = redis.StrictRedis(
                host=redis_host,
                port=redis_port,
                decode_responses=True
            )
            self.redis_pubsub = self.r.pubsub(ignore_subscribe_messages=True)
        except:
            log.info('Failed to connect to Redis')
        self.u = Utils()


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
            The function to execute, is given the kwarg `redis_obj=self.r`
        redis_key: str
            The redis-key that is subscribed to before `func` is executed, 
        message_limit: int = 5
            The maximum number of messages to consider before raising a RuntimeError.
            This includes a lack of a message due to a timeout.
        get_message_timeout: float = 0.5
            The duration after which each iterated `get_message` should timeout.
        
        Return
        ------
        str: the value of the redis_key (`self.r.get(redis_key)`)
        """
        channel = f"__keyspace@0__:{redis_key}"
        self.redis_pubsub.subscribe(channel)
        func(r=self.r)
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
        return self.r.get(redis_key)


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
            lambda **kwargs: kwargs["r"].set("observationQuery", "?"),
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
            lambda **kwargs: kwargs["r"].set("observationExecute", "!"),
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
            HashpipeKeyValues(*instance.split('/'), self.r)
            for instance in instances
        ]
        cosmic_record(
            self.r,
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
                HashpipeKeyValues(*instance.split('/'), self.r)
                for instance in instances
            ]
        )
        return instances

    def is_vlass_obs(self):
        """Check if current observation is a VLASS observation. 
        """
        # VLASS project IDs are TSKY0001 or VLASS*
        scan_id = self.u.hget_decoded(self.r, 'META', 'scanid')
        log.info(scan_id)
        if 'TSKY0001' in scan_id or 'VLASS' in scan_id:
            return True
        else:
            return False

    def is_vlass_cal(self):
        """Check if current observation is a VLASS calibration observation of
        a fixed RA/Dec.
        """
        intents = self.u.hget_decoded(self.r, 'META', 'intents')        
        scan_intent = intents['ScanIntent']
        if self.is_vlass_obs() and 'CALIBRATE' in scan_intent:
            return True
        else:
            return False

    def is_vlass_track(self):
        """Check if current observation is a VLASS track.
        """
        intents = self.u.hget_decoded(self.r, 'META', 'intents')
        scan_intent = intents['ScanIntent']
        log.info(scan_intent)
        if self.is_vlass_obs() and scan_intent == 'OBSERVE_TARGET':
            return True
        else:
            return False

    def vlass_metadata(self):
        """Retrieve VLASS metadata for vlass track observations.
        """
        ra = self.u.hget_decoded(self.r, 'META', 'ra_deg')
        dec = self.u.hget_decoded(self.r, 'META', 'dec_deg')
        # For the purposes of target selection, return the highest 
        # frequency for now (enforce same set of targets for both)
        fcent = max(self.u.hget_decoded(self.r, 'META', 'fcents'))
        intents = self.u.hget_decoded(self.r, 'META', 'intents')
        ra_rate = intents['AntennaRaRate']
        ts = intents['AntennaRatet0']
        return ra, dec, fcent, ra_rate, ts

    def request_targets(self, new_targets_chan, ts, src, ra_deg, dec_deg, fecenter):
        """Request new targets from the target selector.  
        NOTE: Will be replaced with updated targets-minimal process. 
        """
        telescope_name = 12  
        subarray_name = 'array_1'
        msg = '{}:{}:{}:{}:{}:{}:{}'.format(
            telescope_name,
            subarray_name,
            ts,
            src,
            ra_deg,
            dec_deg,
            fecenter
        )
        self.r.publish(new_targets_chan, msg)

    def record_minimal(self, tstart, duration_sec, projid):
        """Minimal initiation of recording. 
        """
        rec_dict = {
            "postprocess":"skip",
            "start_epoch_seconds":tstart,
            "duration_seconds":duration_sec,
            "hashpipe_keyvalues":{"PROJID":projid}
        }
        self.r.set('observationRecord', json.dumps(rec_dict))
    
    def stop_all(self):
        """Wrapper to stop all recording across all nodes. 
        """
        hashpipe_recordStop(redis_obj=self.r)

    def expected_antennas(self, meta_hash='META', antenna_key='station'):
        """Retrieve the list of antennas that are expected to be used 
        for the current observation.
        """
        antennas = self.u.hget_decoded(self.r, meta_hash, antenna_key)
        # Convert to list:
        if antennas is not None:
            return antennas
        else:
            return []

    def on_source_antennas(self, ant_hash='META_flagAnt', on_key='on_source'):
        """Retrieve the list of on-source antennas.
        """
        on_source = self.u.hget_decoded(self.r, ant_hash, on_key)
        if on_source is not None:
            return on_source
        else:
            return []

    def telescope_state(self, stragglers=2, antenna_hash='META_flagAnt', 
        on_key='on_source'):
        """Retrieve the current state of the telescope. This must be 
        achieved by looking at which antennas are actually observing
        as expected. 
        States include:
            unconfigured: no antennas assigned to an observation
            on_source: on source antennas >= off source antennas - stragglers
            off_source: on source antennas < off source antennas - stragglers
        Args:
            stragglers (int): number of off-source stragglers permitted
            when considering the telescope to be on source.  
            antenna_hash (str): hash containing antenna status lists.
            on_key (str): key for the list of on-source antennas. 
        Returns: 
            state (str): telescope state. 
        """ 
        # Max list of antennas expected 
        antennas = self.expected_antennas()
        if len(antennas) > 0:
            # Retrieve on source antennas:
            on_source = self.on_source_antennas()
            if len(on_source) >= (len(antennas) - stragglers):
                return 'on_source'
            else:
                return 'off_source'
        else:
            self.u.alert('Telescope unconfigured')
            return 'unconfigured'

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
