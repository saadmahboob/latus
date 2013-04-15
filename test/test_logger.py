
import logging
from .. import logger

def print_all_levels(log, msg = ""):
    log.error('"error test message %s"', msg)
    log.warning('"warning test message %s"', msg)
    log.info('"info test message %s"', msg)
    log.debug('"debug test message %s"', msg)

def test_logger():
    log = logger.get_log()
    log_handlers = logger.setup()

    print_all_levels(log, "default")

    # print debugging level to the console by setting the global level to DEBUG but file to WARNING
    log.setLevel(logging.DEBUG)
    log_handlers['file'].setLevel(logging.WARNING)
    print_all_levels(log, "console debugging")

    logger.remove_handlers(log_handlers)

if __name__ == '__main__':
    test_logger()