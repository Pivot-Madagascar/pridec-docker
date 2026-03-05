def setup_logging():
    import logging

    from config import LOG_LEVEL

    logging.basicConfig(format='%(asctime)s | %(levelname)s | %(name)s | %(message)s', 
                        level=getattr(logging, LOG_LEVEL, logging.INFO),
                        datefmt="%Y-%m-%dT%H:%M:%S",
                        force=True)
