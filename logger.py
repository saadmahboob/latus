
import sys
import logging
import logging.handlers

""" General logging capability.

Good rules of thumb on using logging levels:
http://en.wikipedia.org/wiki/Log4j
"""

# Only one call should be made to this per program invocation (or else you'll get repeated lines in the log)
#
# We default stream_out to sys.stdout so the "nose" testing framework can consume the output, but
# in normal operation logs still get sent to the console.  If this over-use of stdout is not the desired
# behavior, users of these functions can set it 'back' to None so it'll use the default StreamHandler stream,
# which is currently sys.stderr.
#

# this is usually used as a default
def get_log_file_path():
    return "latus.log"

def setup(log, get_log_file_path = get_log_file_path, max_bytes = 1000000, stream_out = sys.stdout):
    # note that (message) is not pre-quoted, in case there are multiple fields
    format_string = '"%(asctime)s","%(name)s","%(levelname)s","module","%(module)s","line","%(lineno)d",%(message)s'
    handlers = {}

    # create console handler
    console_handler = logging.StreamHandler(stream_out)
    console_formatter = logging.Formatter(format_string)
    console_handler.setFormatter(console_formatter)
    log.addHandler(console_handler)
    handlers['console'] = console_handler

    # create file handler
    file_handler = logging.handlers.RotatingFileHandler(get_log_file_path(), maxBytes=max_bytes)
    file_formatter = logging.Formatter(format_string)
    file_handler.setFormatter(file_formatter)
    log.addHandler(file_handler)
    handlers['file'] = file_handler

    return handlers

def remove_handlers(log, handlers):
    for handler in handlers:
        log.removeHandler(handler)