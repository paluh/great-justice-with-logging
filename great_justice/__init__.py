# -*- coding: utf-8 -*-

'''
great-justice:

A more useful alternative to regular stack traces.
'''

import contextlib
import sys
import time
import traceback

from . import structure
from . import utils

__version__ = '1.0.1'

__all__ = ['what_happen', 'take_your_time', 'we_get_signal']

def what_happen(logger=None):
    '''
    Print information about the current stack trace
    '''
    trace = utils.Trace(sys.exc_info())
    if not logger:
        for info, indent in trace.stack:
            lines = info.prettyformat().splitlines()
            for line in lines:
                print '  ' * indent + line
            #pprint.pprint(unicode(trace))
    else:
        logger.log(unicode(trace))

@contextlib.contextmanager
def take_your_time(logger=None):
    '''
    Trap errors occuring inside this context processor and print them
    using what_happen
    '''
    try:
        yield
    except Exception: # pylint: disable=W0703
        what_happen(logger=logger)
        raise


class Signal(object):
    '''
    Context manager class for logging calls
    '''
    # pylint: disable=R0903
    logger = None
    _old_trace = None
    _indent = 0
    _timers = None

    def __init__(self, logger=None):
        self.logger = logger
        self._timers = []

    def __enter__(self):
        self._old_trace = sys.gettrace()
        sys.settrace(self.log_call)

    def __exit__(self, *args):
        sys.settrace(self._old_trace)

    def log_call(self, frame, event, arg):
        '''
        Processes the event and displays it accordingly
        '''
        if event == 'call':
            if utils.is_own_frame(frame):
                return
            utils.log_invocation(self.logger, frame, indent=self._indent)
            self._indent += 1
            self._timers.append(time.time())
        elif event == 'return':
            self._indent -= 1
            duration = '(%.5f s)' % (time.time() - self._timers.pop(), )
            utils.log(self.logger, structure.CallReturn(arg, duration),
                      indent=self._indent)
        elif event == 'exception':
            utils.log_call(self.logger, frame, indent=self._indent)
            utils.log(
                self.logger, structure.ExceptionValue(
                    ''.join(
                        traceback.format_exception_only(arg[0],
                                                        arg[1])).strip()),
                indent=self._indent)
        return self.log_call


we_get_signal = Signal

