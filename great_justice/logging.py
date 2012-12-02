from __future__ import absolute_import
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from logging import _defaultFormatter, Formatter, StreamHandler
from logging.handlers import SMTPHandler
import os
import smtplib
import sys
from termcolor import colored

from . import structure
from . import utils


class Formatter(Formatter):

    def formatException(self, ei):
        s = unicode(utils.Trace(ei))
        if s[-1:] == "\n":
            s = s[:-1]
        return s


class HtmlFormatter(Formatter):

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

    def format(self, record, html=False):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self._fmt % record.__dict__
        if record.exc_info:
            if html:
                s = '<p style="white-space: pre-wrap; word-wrap: break-word;">%s</p>' % s
                exc_html = self.formatException(record.exc_info, html)
                s = s + exc_html
            else:
                if not record.exc_text:
                    record.exc_text = self.formatException(record.exc_info)
                if s[-1:] != "\n":
                    s = s + "\n"
                try:
                    s = s + record.exc_text
                except UnicodeError:
                    s = s + record.exc_text.decode(sys.getfilesystemencoding(),
                                                   'replace')
        return s

    def formatException(self, ei, html=False):
        if not html:
            return super(HtmlFormatter, self).formatException(ei)
        trace = utils.Trace(ei)
        escape = lambda s: (s.replace('&', '&amp;')
                             .replace('>', '&gt;')
                             .replace('<', '&lt;')
                             .replace("'", '&#39;')
                             .replace('"', '&#34;'))
        output = ['<div style="color:#fff;background:#000;font-size:12px;font-family:monospace;white-space:pre;padding:10px">']
        def prettyformat(struct, indent):
            o = []
            def _prettyformat(struct):
                if type(struct) in self.styles:
                    o.append(u'<span style="%s">'% self.styles[type(struct)])
                for arg in struct.args:
                    if isinstance(arg, structure.Structure):
                        _prettyformat(arg)
                    else:
                        o.append(escape(unicode(arg)))
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
        super(SMTPHandler, self).__init__(*args, **kwargs)
        self.formatter = self.formatter or HtmlFormatter()

    def emit(self, record):
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = self.getSubject(record)
            msg['From'] = self.fromaddr
            msg['To'] = ",".join(self.toaddrs)
            msg['Date'] = formatdate()

            text = self.format(record)
            msg.attach(MIMEText(text.encode(sys.getfilesystemencoding()), 'plain'))
            if record.exc_info:
                html = self.format(record, html=True)
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

    def format(self, record, html=False):
        if self.formatter and isinstance(self.formatter, HtmlFormatter):
            return self.formatter.format(record, html)
        if self.formatter:
            fmt = self.formatter
        else:
            fmt = _defaultFormatter
        return fmt.format(record)


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

    def formatException(self, ei, isatty=False):
        if not isatty:
            return super(TermFormatter, self).formatException(ei)
        trace = utils.Trace(ei)
        def prettyformat(struct, indent):
            def _prettyformat(struct):
                attrs = self.styles.get(type(struct), {})
                return colored(
                    u''.join(_prettyformat(arg)
                    if isinstance(arg, structure.Structure) else unicode(arg)
                    for arg in struct.args), **attrs)
            i = u'  '*indent
            return u'\n'.join([i+l for l in ''.join(_prettyformat(struct)).splitlines()])
        return '\n'.join(prettyformat(info, indent) for info, indent in trace.stack)

    def format(self, record, isatty=False):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self._fmt % record.__dict__
        if record.exc_info:
            exc_text = self.formatException(record.exc_info, isatty)
            if s[-1:] != "\n":
                s = s + "\n"
            try:
                s = s + exc_text
            except UnicodeError:
                s = s + exc_text.decode(sys.getfilesystemencoding(), 'replace')
        return s


class StreamHandler(StreamHandler):

    def __init__(self, *args, **kwargs):
        super(StreamHandler, self).__init__(*args, **kwargs)
        self.formatter = self.formatter or TermFormatter()

    def format(self, record):
        if self.formatter and isinstance(self.formatter, TermFormatter):
            return self.formatter.format(record, os.isatty(self.stream.fileno()))
        if self.formatter:
            fmt = self.formatter
        else:
            fmt = _defaultFormatter
        return fmt.format(record)
