import redis

class Interface(object):
    """Observing interface library.
    
    Offers the following:
        - Initiate configuration
        - Request new target lists
        - Initiate recording
        - Initiate processing
        - Run any cleanup functions
    """

    def configure(self, antennas, fcents, fenpol, obsbwmhz, samplehz):
        """
        return 0 if successful; return error code if not. 
        """

    def record(self, src, ra_deg, dec_deg):
        """
        return 0 if successful; return error code if not. 
        Needs to return directory for recording (NVMe file path). 
        """
    
    def process(self):
        """
        return 0 if successful; return error code if not. 
        Needs to return directory for data products.
        """
    
    def cleanup(self):
        """
        return 0 if successful; return error code if not. 
        """


    def request_targets(self, new_targets_chan, obs_ts, src, ra_deg, dec_deg, fcents):
        """Request new targets from the target selector. Publishes a special 
        formatted Redis message containing appropriate metadata to the new 
        targets channel of the target selector.

        Args: 
        
            new_targets_chan (str): Redis channel from which the target
            selector expects new target list requests.
            meta (dict): Metadata dictionary for the current observation. 
        
        """
        telescope_name = 12  
        subarray_name = 'array_1'
        # Use max frequency for conservative field of view estimate
        fecenter = max(fcents)

        msg = '{}:{}:{}:{}:{}:{}:{}'.format(telescope_name,
                                            subarray_name,
                                            obs_ts,
                                            src,
                                            ra_deg,
                                            dec_deg,
                                            fecenter)

        self.redis_obj.publish(new_targets_chan, msg)

        logging.info('Requested new targets for {} at {}'.format(src_name, obs_ts))