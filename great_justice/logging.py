from __future__ import absolute_import
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from logging import _defaultFormatter, Formatter
from logging.handlers import SMTPHandler
import smtplib
import sys

from . import structure
from . import utils


class Formatter(Formatter):

    def format(self, record):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self._fmt % record.__dict__
        if record.exc_info:
            record.exc_text = unicode(utils.Trace(record.exc_info))
        if record.exc_text:
            if s[-1:] != '\n':
                s = s + '\n'
            s =  s +  record.exc_text
        return s


class SMTPHandler(SMTPHandler):

    def __init__(self, *args, **kwargs):
        super(SMTPHandler, self).__init__(*args, **kwargs)
        self.formatter = Formatter()

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
                info = (self.formatter or _defaultFormatter)._fmt % record.__dict__
                info = '<p style="white-space: pre-wrap; word-wrap: break-word;">%s</p>' % info
                trace_html = self._trace_html(utils.Trace(record.exc_info))
                html = ('<html><head></head><body>%s<div style="font-size:120%%">%s</div></body></html>')% (info, trace_html)
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

    def _trace_html(self, trace):
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
        escape = lambda s: (s.replace('&', '&amp;')
                             .replace('>', '&gt;')
                             .replace('<', '&lt;')
                             .replace("'", '&#39;')
                             .replace('"', '&#34;'))
        output = ['<div style="color:#fff;background:#000;font-size:12px;font-family:monospace;white-space:pre;padding:10px">']
        def prettyformat(struct, indent):
            o = []
            def _prettyformat(struct):
                if struct.__class__ in styles:
                    o.append(u'<span style="%s">'% styles[struct.__class__])
                for arg in struct.args:
                    if isinstance(arg, structure.Structure):
                        _prettyformat(arg)
                    else:
                        o.append(escape(unicode(arg)))
                if struct.__class__ in styles:
                    o.append(u'</span>')
            _prettyformat(struct)
            i = u'  '*indent
            return u'\n'.join([i+l for l in ''.join(o).splitlines()])
        for struct, indent in trace.stack:
            output.append(prettyformat(struct, indent))
        output.append('</div>')
        return '\n'.join(output)

