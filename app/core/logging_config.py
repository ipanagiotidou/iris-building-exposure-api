# LOGGING - instead of print - it gives ability to control the verbosity 
import logging 

def setup_logging(level: int = logging.INFO) -> None:
    """
    Defines the minimum logging level.
    The format 
    the timestamp and module name ! 

    IMPROVEMENT: Later, we can extend it to write logs to files as well.

    """

    logging.basicConfig(
        level= level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


