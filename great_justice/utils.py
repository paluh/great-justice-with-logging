# -*- coding: utf-8 -*-

'''
Helper utils
'''

import inspect
import linecache
import pprint
import traceback

from . import structure


class Trace(object):

    def __init__(self, exc_info):
        exc_type, exc_value, trace = exc_info
        self.stack = [(structure.WhatHappen(),0)]
        while trace:
            frame = trace.tb_frame
            trace = trace.tb_next
            if not is_own_frame(frame):
                filename = inspect.getsourcefile(frame)
                self.stack.append((structure.FileReference(filename, frame.f_lineno, frame.f_code.co_name), 0))
                self.stack.extend(self._parse_frame(frame))
        self.stack.append((structure.ExceptionValue(''.join(traceback.format_exception_only(exc_type, exc_value)).strip()), 0))

    def _parse_frame(self, frame, indent=0):
        prefix, line, suffix = get_source(frame)
        missing = object()
        stack = []
        if line:
            stack.append((structure.Code(prefix, line, suffix), indent+1))
            for key in sorted(frame.f_code.co_varnames):
                value = frame.f_locals.get(
                    key,
                    frame.f_globals.get(
                         key,
                         frame.f_builtins.get(key, missing)))
                if value is not missing:
                    try:
                        value = pprint.pformat(value, width=60)
                    except Exception: # pylint: disable=W0703
                        stack.append((structure.ShortVariable( key, '<EXCEPTION RAISED WHILE TRYING TO PRINT>'),
                                      indent+2))
                    else:
                        if value.count('\n'):
                            stack.append((structure.LongVariable(key), indent+2))
                            stack.append((structure.Value(value), indent+3))
                        else:
                            stack.append((structure.ShortVariable(key, value), indent+2))
                else:
                    stack.append((structure.UndefinedVariable(key), indent+2))
        return stack

    def __unicode__(self):
        value = []
        for info, indent in self.stack:
            lines = unicode(info).splitlines()
            for line in lines:
                value.append('  ' * indent + line)
        return '\n'.join(value)


def is_own_frame(frame):
    '''
    Returns True if given frame points to us
    '''
    filename = inspect.getsourcefile(frame)
    # skip self
    filename_base = filename.rsplit('.', 1)[0]
    local_base = __file__.rsplit('.', 1)[0]
    if filename_base == local_base:
        return True
    return False

def get_source(obj):
    '''
    Get the source code for the frame object
    '''
    filename = inspect.getsourcefile(obj)
    linecache.checkcache(filename)
    lineno = inspect.getlineno(obj)
    prefix = [(linecache.getline(filename, ln) or u'~').strip('\r\n')
              for ln in range(lineno-3, lineno)]
    current = linecache.getline(filename, lineno).strip('\r\n')
    suffix = [(linecache.getline(filename, ln) or u'~').strip('\r\n')
              for ln in range(lineno+1, lineno+4)]
    return prefix, current, suffix


def log(logger, info, indent=0):
    '''
    Either log a clean version of info or print its colorful version
    if no logger is provided
    '''
    if logger:
        lines = unicode(info).splitlines()
        for line in lines:
            logger.debug('  ' * indent + line)
    else:
        lines = info.prettyformat().splitlines()
        for line in lines:
            print '  ' * indent + line

def log_call(logger, frame, indent=0):
    '''
    Displays the filename and line no.
    '''
    filename = inspect.getsourcefile(frame)
    log(logger,
        structure.FileReference(filename, frame.f_lineno, frame.f_code.co_name),
        indent=indent)

def log_invocation(logger, frame, indent=0):
    '''
    Displays the filename, line no. and the function being called
    along with its params
    '''
    log_call(logger, frame, indent=indent)

    arguments = dict(
        (key, pprint.pformat(
            frame.f_locals.get(key, frame.f_globals.get(key))))
        for key in frame.f_code.co_varnames)
    log(logger,
        structure.Call(frame.f_code.co_name, arguments),
        indent=indent)

