#!/usr/bin/env python
'''
This script is supposed to periodically (e.g. one-minute cronjob) download the
list of calls from your Alice/O2 DSL router.
It searches the list for incoming missed calls which are new since the last
run of the script and sends them per email to configurable addresses.
'''
import sys
import datetime
import urllib2
import csv
import smtplib
from email.mime.text import MIMEText

URL = 'http://alice.box/cgi-bin/Anrufliste.csv'
ENCODING = 'utf-16'

TIMESTAMP = '/tmp/phony'
DATETIME_FMT = '%d.%m.%Y %H:%M:%S'

SMTP_HOST = None
SMTP_TLS = False
SMTP_USER = None
SMTP_PASS = None

TO = ['user1@example.com', 'user2@example.com']
FROM = 'phone@example.com'

if __name__ == '__main__':
    r = urllib2.urlopen(URL)
    assert 200 <= r.getcode() < 300

    text = r.read().decode(ENCODING).encode('utf-8')

    dialect = csv.Sniffer().sniff(text)

    l = []
    for d in csv.DictReader(text.splitlines(), dialect=dialect):
        dd = {}
        for k in d:
            kk = unicode(k, encoding='utf-8')
            vv = unicode(d[k], encoding='utf-8')
            dd[kk] = vv
        l.append(dd)

    try:
        timestamp = datetime.datetime.strptime(open(TIMESTAMP).read().strip(), DATETIME_FMT)
    except:
        timestamp = datetime.datetime.fromtimestamp(0)
    
    s = []
    for d in reversed(l):
        ts = datetime.datetime.strptime(d[u'Zeitpunkt'], DATETIME_FMT)
        if d[u'Art'] == u'eingehend verpasst' and ts > timestamp:
            s.append(u'Zeitpunkt: %(Zeitpunkt)s, Rufnummer: %(Rufnummer)s' % d)  

    if s:
        subject = u'%d ' % len(s) + ('verpasster Anruf' if len(s) == 1 else 'verpasste Anrufe')
        msg = subject + u' seit %s\n' % (timestamp.strftime(DATETIME_FMT)) + '=' * 78 + '\n\n' + '\n'.join(s)

        mail = MIMEText(msg)
        mail['Subject'] = subject
        mail['From'] = FROM
        mail['To'] = ', '.join(TO)

        if SMTP_HOST:
            s = smtplib.SMTP(SMTP_HOST)
            if SMTP_TLS:
                s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(FROM, TO, mail.as_string())
            s.quit()
        else:
            print mail.get_payload()

    if not '-n' in sys.argv:
       open(TIMESTAMP, 'w').write(datetime.datetime.now().strftime(DATETIME_FMT))
