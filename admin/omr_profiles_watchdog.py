#!/usr/bin/env python3
"""Recover abandoned VPS profile changes independently of the API process."""
import logging
import omr_profiles

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    runtime = omr_profiles.Runtime(omr_profiles.watchdog_control,
                                  omr_profiles.ensure_system_nanbbr,
                                  omr_profiles.watchdog_read_nanbbr)
    try:
        omr_profiles.ProfileManager(runtime, enable_timer=False).startup()
    except Exception:
        logging.exception('OMR profile recovery failed; the next timer tick will retry')
        raise
