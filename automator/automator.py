import redis
import time

from interface import Interface
from logger import log
from utils import Utils

from astropy.coordinates import SkyCoord
import astropy.units as u

TARGETS_CHAN = "target-selector:new-pointing"

class Automator(object):
    """Automation for observations.
    This process coordinates the initiation of observations with
    observations possible. See `interface.py` for the atomic actions
    that enable this.

    """

    def __init__(self, redis_endpoint, redis_channel):
        """Construct an Automator.

        Args:
            redis_endpoint (str): Redis endpoint (of the form
            <host IP address>:<port>)
        """ 
        redis_host, redis_port = redis_endpoint.split(':')
        # Redis connection:
        self.r = redis.StrictRedis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        # Utilities:
        self.u = Utils()
        # Interface:
        self.interface = Interface(
            redis_host,
            redis_port
        )
        self.channel = redis_channel

    def start(self):
        """Start the automator. Actions to be taken depend on the incoming 
        observational stage messages on the appropriate Redis channel. 
        """   
        
        self.u.alert('Starting up...')
        ps = self.r.pubsub(ignore_subscribe_messages=True)
        ps.subscribe(self.channel)

        for msg in ps.listen():

            # Upon receiving a new alert message, 
            # check if the telescope is tracking
            if msg['data'] == 'on_source':

                # Check if VLASS observation:
                if self.interface.is_vlass_calibrator():
                   # Record (for how long?)

                if self.interface.is_vlass_track():
                    
                    # Retrieve metadata:
                    ra, dec, fcent, ra_rate, ts = self.interface.vlass_metadata()

                    # Calculate phase center:
                    # Using VLASS standard slew rate of 3.3 arcmin/sec (0.055 deg/sec) 
                    # until ra_rate units are understood
                    ra_c, dec_c = self.select_phase_center(0.055, ts, ra, dec)
                    self.r.set('phase_center_ra', '{ra_c}')
                    self.r.set('phase_center_dec', '{dec_c}')

                    # Request new targets around phase center
                    self.interface.request_targets(
                        TARGETS_CHAN, 
                        ts, 
                        'VLASS', 
                        ra_c, 
                        dec_c, 
                        fcent
                        )
                    
                    # Instruct recording to start


            if msg['data'] == 'off_source':

                # Stop recording

    def offset_ra(self, angle, ra, dec):
        """Return new RA given a separation.
        """
        start = SkyCoord(ra, dec, units="deg")
        offset = start.directional_offset_by(90*u.deg, angle*u.deg)
        return offset.ra.degree, offset.dec.degree

    def mjd_now(self):
        return time.time()/86400.0 + 40587.0

    def select_phase_center(self, slew_rate, t_start, ra, dec):
        """Select coordinates based on slew_rate, coordinates and time.
        """
        # Separation since packet received (5 seconds to phase center)
        # Add another buffer of 1 second (will specify tstart 1 sec in 
        # the future)
        ra_sep_start = (self.mjd_now() - t_start + 6)*slew_rate
        ra, dec = self.offset_ra(ra_sep_start, ra, dec)
        return ra, dec


