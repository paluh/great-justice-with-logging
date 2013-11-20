from __future__ import absolute_import
import argparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from logging import Formatter, getLogger, StreamHandler
from logging.handlers import SMTPHandler
import os
import smtplib
import sys
from termcolor import colored

from . import structure
from . import utils


class Formatter(Formatter):

    def _formatTrace(self, trace):
        s = unicode(trace)
        if s[-1:] == "\n":
            s = s[:-1]
        return s

    def formatException(self, ei):
        trace = utils.Trace(ei)
        return self._formatTrace(trace)


class HtmlFormatter(Formatter):

    header_container_style = 'white-space: pre-wrap; word-wrap: break-word;'
    trace_container_style = ('color:#fff;background:#000;font-size:14px;'
                             'font-family:monospace;white-space:pre;padding:10px')
    styles = {
        structure.WhatHappen: 'color:red',
        structure.VariableName: 'color:yellow',
        structure.Value: 'color:green',
        structure.UndefinedValue: 'color:red',
        structure.CurrentLine: 'font-weight:bold;color:white',
        structure.CodeLine: 'font-weight:grey',
        structure.CodeScope: 'font-weight:bold',
        structure.CodeLineNo: 'font-weight:bold',
        structure.ExceptionValue: 'font-weight:bold;color:red',
    }

    def __init__(self, *args, **kwargs):
        self._max_trace_item_length = kwargs.pop('max_trace_item_length', None)
        super(Formatter, self).__init__(*args, **kwargs)


    def format(self, record):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self._fmt % record.__dict__
        if record.exc_info:
            exc_html = self.formatException(record.exc_info)
            s = '<p style="%s">%s</p>' % (self.header_container_style, s)
            s = s + exc_html
        return s

    def _cutTraceItemString(self, element_string):
        if (self._max_trace_item_length is None or
            len(element_string) < self._max_trace_item_length):
            return element_string
        element_string = ('%s' % element_string[:(self._max_trace_item_length - 3)])
        return '%s&hellip;' % element_string

    def _formatTrace(self, trace):
        escape = lambda s: (s.replace('&', '&amp;')
                             .replace('>', '&gt;')
                             .replace('<', '&lt;')
                             .replace("'", '&#39;')
                             .replace('"', '&#34;'))
        output = ['<div style="%s">' % self.trace_container_style]

        def prettyformat(struct, indent):
            o = []
            def _prettyformat(struct):
                if type(struct) in self.styles:
                    o.append(u'<span style="%s">'% self.styles[type(struct)])
                for arg in struct.args:
                    if isinstance(arg, structure.Structure):
                        _prettyformat(arg)
                    elif isinstance(arg, basestring):
                        o.append(self._cutTraceItemString(escape(structure._decode(arg))))
                    else:
                        o.append(self._cutTraceItemString(escape(unicode(arg))))
                if type(struct) in self.styles:
                    o.append(u'</span>')
            _prettyformat(struct)
            i = u'  '*indent
            return u'\n'.join([i+l for l in ''.join(o).splitlines()])
        for struct, indent in trace.stack:
            output.append(prettyformat(struct, indent))
        output.append('</div>')
        return '\n'.join(output)


class SMTPHandler(SMTPHandler):

    def __init__(self, *args, **kwargs):
        formatter = kwargs.pop('formatter', Formatter())
        self.html_formatter = kwargs.pop('html_formatter', HtmlFormatter())
        super(SMTPHandler, self).__init__(*args, **kwargs)
        self.formatter = formatter

    def emit(self, record):
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = self.getSubject(record)
            msg['From'] = self.fromaddr
            msg['To'] = ",".join(self.toaddrs)
            msg['Date'] = formatdate()

            text = self.format(record)
            msg.attach(MIMEText(text.encode(sys.getfilesystemencoding()), 'plain'))
            if record.exc_info and self.html_formatter:
                html =  self.html_formatter.format(record)
                html = '<html><head></head><body>%s</body></html>' % html
                msg.attach(MIMEText(html.encode(sys.getfilesystemencoding()), 'html'))
            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            smtp = smtplib.SMTP(self.mailhost, port)
            if self.username:
                if self.secure is not None:
                    smtp.ehlo()
                    smtp.starttls(*self.secure)
                    smtp.ehlo()
                smtp.login(self.username, self.password)
            smtp.sendmail(self.fromaddr, self.toaddrs, msg.as_string())
            smtp.quit()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class TermFormatter(Formatter):

    styles = {
        structure.WhatHappen: {'color': 'red'},
        structure.VariableName: {'color': 'yellow'},
        structure.Value: {'color': 'green'},
        structure.UndefinedValue: {'color': 'red'},
        structure.CurrentLine: {'color': 'white', 'attrs': ['bold']},
        structure.CodeLine: {'color': 'blue'},
        structure.CodeScope: {'attrs': ['bold']},
        structure.CodeLineNo: {'attrs': ['bold']},
        structure.ExceptionValue: {'color': 'red', 'attrs': ['reverse']}
    }

    def __init__(self, *args, **kwargs):
        self._max_trace_item_length = kwargs.pop('max_trace_item_length', None)
        super(Formatter, self).__init__(*args, **kwargs)


    def _formatTrace(self, trace):
        """Format internal traceback representation"""
        def prettyformat(struct, indent):
            def _prettyformat(struct):
                attrs = self.styles.get(type(struct), {})
                return colored(
                    u''.join(_prettyformat(arg)
                    if isinstance(arg, structure.Structure) else self._cutTraceItemString(unicode(arg))
                    for arg in struct.args), **attrs)
            i = u'  '*indent
            return u'\n'.join([i+l for l in ''.join(_prettyformat(struct)).splitlines()])
        return '\n'.join(prettyformat(info, indent) for info, indent in trace.stack)

    def _cutTraceItemString(self, element_string):
        if (self._max_trace_item_length is None or
            len(element_string) < self._max_trace_item_length):
            return element_string
        element_string = ('%s' % element_string[:(self._max_trace_item_length - 3)])
        return element_string.ljust(self._max_trace_item_length, '.')


    def format(self, record):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self._fmt % record.__dict__
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            if s[-1:] != "\n":
                s = s + "\n"
            try:
                s = s + exc_text
            except UnicodeError:
                s = s + exc_text.decode(sys.getfilesystemencoding(), 'replace')
        return s


class StreamHandler(StreamHandler):

    def __init__(self, *args, **kwargs):
        formatter = kwargs.pop('formatter', Formatter())
        self.term_formatter = kwargs.pop('term_formatter', None)
        super(StreamHandler, self).__init__(*args, **kwargs)
        if self.term_formatter is None and (hasattr(self.stream, 'fileno') and
                                            os.isatty(self.stream.fileno())):
            self.term_formatter = TermFormatter()
        self.formatter = formatter

    def format(self, record):
        if self.term_formatter:
            return self.term_formatter.format(record)
        return super(StreamHandler, self).format(record)


if __name__ == '__main__':
    # usage: python -mgreat_justice.logging
    logger = getLogger()
    parser = argparse.ArgumentParser(prog='logging')
    # you can chek email version of logging too
    subparsers = parser.add_subparsers()
    mail_parser = subparsers.add_parser('mail')
    mail_parser.add_argument('--host', help='Mail server domain', required=True)
    mail_parser.add_argument('--port', help='Mail server port', type=int, required=True)
    mail_parser.add_argument('--fromaddr', help='Sender address', required=True)
    mail_parser.add_argument('--toaddress', help='Recipient address', required=True)
    mail_parser.add_argument('--subject', help='Mail subject', default='Log message')
    mail_parser.add_argument('--username', required=False)
    mail_parser.add_argument('--password', required=False)
    mail_parser.add_argument('--unsecure', action='store_false')

    console_handler = StreamHandler(sys.stdout, formatter=Formatter(),
                                    term_formatter=TermFormatter())
    logger.addHandler(console_handler)
    def add_email_handler(args):
        credentials = (args.username, args.password)
        email_handler = SMTPHandler((args.host, args.port), args.fromaddr, [args.toaddress],
                                    args.subject, credentials=credentials,
                                    secure=None if args.unsecure else (),
                                    formatter=Formatter(), html_formatter=HtmlFormatter())
        logger.addHandler(email_handler)
    mail_parser.set_defaults(func=add_email_handler)

    if len(sys.argv) > 1:
        args = parser.parse_args()
        args.func(args)

    # generate some trace
    def function(x):
        if x == 'step on':
            raise ValueError('Don\'t tread on me!')

    try:
        y = 'step on'
        function(y)
    except Exception, e:
        a = 99
        logger.exception(e)
