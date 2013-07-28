#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
This script is supposed to periodically (e.g. one-minute cronjob) download the
list of calls from your Alice/O2 DSL router.
It searches the list for incoming missed calls which are new since the last
run of the script and sends them per email to configurable addresses.

Of course, this script can't be used on the router itself, since you can't
put custom software there. But you can for example run this script on your
Raspberry Pi or your NAS.

All dependencies should be in the Python standard library, so you don't need to
install any packages to run phony.
'''
import sys
import os
import ConfigParser
import datetime
import urllib2
import csv
import smtplib
from email.mime.text import MIMEText

CONFIG_LOCATIONS = ['/etc/phony.ini', '~/.phony.ini', './phony.ini',
        os.path.join(os.path.dirname(os.path.realpath(__file__)), 'phony.ini')]

if __name__ == '__main__':

    conf = ConfigParser.RawConfigParser(allow_no_value=True)
    conffiles = conf.read([os.path.abspath(os.path.expanduser(loc)) for loc in CONFIG_LOCATIONS])
    if not conffiles:
        raise Exception('No config file at all could be found...')

    TIMESTAMP = conf.get('timestamp', 'timestamp_file')
    DATETIME_FMT = conf.get('timestamp', 'datetime_format')

    URL = conf.get('datasource', 'url')
    ENCODING = conf.get('datasource', 'encoding')

    TYPE_FILTER = conf.get('datasource', 'type_filter')

    MAPPING = {}
    for v in conf.options('mapping'):
        MAPPING[conf.get('mapping', v)] = v

    try:
        timestamp = datetime.datetime.strptime(open(TIMESTAMP).read().strip(), DATETIME_FMT)
    except:
        timestamp = datetime.datetime.fromtimestamp(0)
    timestamp_str = timestamp.strftime(DATETIME_FMT)

    r = urllib2.urlopen(URL)
    assert 200 <= r.getcode() < 300

    text = r.read().decode(ENCODING).encode('utf-8')
    dialect = csv.Sniffer().sniff(text)

    l = []
    for d in csv.DictReader(text.splitlines(), dialect=dialect):
        dd = {}
        for k in d:
            if k in MAPPING:
                kk = MAPPING[k]
                if kk == 'timestamp':
                    dd['timestamp'] = datetime.datetime.strptime(d[k], DATETIME_FMT)
                    dd['timestamp_str'] = dd['timestamp'].strftime(DATETIME_FMT)
                else:
                    dd[kk] = unicode(d[k], encoding='utf-8')
        if dd['type'] in TYPE_FILTER and dd['timestamp'] > timestamp:
            l.append(dd)

    if l:
        count = len(l)
        subject = conf.get('template', 'subject_line_one' if count == 1 else 'subject_line_more') % {'count': count, 'timestamp_str': timestamp_str}

        msg = conf.get('template', 'title_line') % {'subject_line': subject, 'timestamp_str': timestamp_str} + '\n' + '=' * 78 + '\n\n'

        call_line = conf.get('template', 'call_line')
        for ll in l:
            msg += call_line % ll

        mail = MIMEText(msg)
        mail['Subject'] = subject

        if not '-n' in sys.argv and not '--no-mail' in sys.argv and conf.has_section('mail'):
            try:
                SMTP_HOST = conf.get('mail', 'smtp_host')
                SMTP_SEC = conf.get('mail', 'smtp_security')
                SMTP_USER = conf.get('mail', 'smtp_username')
                SMTP_PASS = conf.get('mail', 'smtp_password')

                FROM = conf.get('mail', 'from')
                TO = [m.strip() for m in conf.get('mail', 'to').split(',')]

                mail['From'] = FROM
                mail['To'] = ', '.join(TO)

                if SMTP_SEC.lower() == 'ssl':
                    s = smtplib.SMTP_SSL(SMTP_HOST)
                else:
                    s = smtplib.SMTP(SMTP_HOST)
                if SMTP_SEC.lower() == 'tls':
                    s.starttls()
                s.login(SMTP_USER, SMTP_PASS)
                s.sendmail(FROM, TO, mail.as_string())
                s.quit()
            except:
                print mail.as_string()
                raise
        else:
            print mail.get_payload()

    if not '-n' in sys.argv and not '--no-timestamp' in sys.argv:
       open(TIMESTAMP, 'w').write(datetime.datetime.now().strftime(DATETIME_FMT))
