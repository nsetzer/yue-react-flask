
"""
Utility module for converting strings into dates,
used as part of the search grammar
"""

import re
"""

last n hours
last n days
last n weeks
last n months

n hours ago [to <date>]
n days ago [to <date>]
n weeks ago [to <date>]
n months ago [to <date>]
n years ago [to <date>]

units: + plural with 's'
 hour,day,week,month,year
 hours,days,weeks,months,years

5 special words:
  yesterday
  last week
  last month
  last year
  today

2 grammers:
  date:
    last <unit> | <special word>
    last n <unit> [to <unit>]
      all songs from n units until today.

    n <unit> [ago] [to <date>]
    n <unit> [ago] to m <unit> [ago]

return a date range base on natural language.

"""
import datetime
from calendar import monthrange,isleap,timegm

def ppdt(dt):
    return "%s/%02s/%02s (%s) %02s:00"%(dt.year,dt.month,dt.day,
                                        dt.weekday(),dt.hour)

def unit_start(dt,offset,unit):
    """
    for each time-scale unit, year,month,week,day,hour
    return the 'start' of its kind
        'year' returns january 1st of this year
        'month' return 1st of this month
        'day' returns 0:00 this morning
        'week' returns 0:00 on the most recent monday
        'hour' return H:00 on this hour
    """
    weekday_offset=1 # set to one for sunday being first day of the week
    #dt = datetime.datetime.now();
    if unit.endswith('s'):
        unit = unit[:-1]
    if unit == 'year':
        dt = datetime.datetime(dt.year + offset,1,1)
    if unit == 'month':
        year = dt.year
        month = dt.month + offset
        while month < 1:
            month += 12
            year -= 1
        dt = datetime.datetime(year,month,1)
    elif unit == 'week':
        dt = datetime.datetime(dt.year,dt.month,dt.day) \
            - datetime.timedelta(days=weekday_offset+dt.weekday()-7*offset)
    elif unit == 'day':
        dt = datetime.datetime(dt.year,dt.month,dt.day)
        dt = dt - datetime.timedelta(days=-offset)
    elif unit == 'hour':
        dt = datetime.datetime(dt.year,dt.month,dt.day,dt.hour)
        dt = dt - datetime.timedelta(hours=-offset)
    return dt

def unit_delta(dt,unit):
    """ return a time delta object representing 1 unit."""
    year  = dt.year
    month = dt.month
    if unit.endswith('s'):
        unit = unit[:-1]
    delta = None
    if unit == 'year':
        delta= datetime.timedelta(366 if isleap(year) else 365 )
    if unit == 'month':
        delta= datetime.timedelta(monthrange(year,month)[1])
    if unit == 'week':
        delta= datetime.timedelta(7)
    if unit == 'day':
        delta= datetime.timedelta(1)
    if unit == 'hour':
        delta= datetime.timedelta(hours=1)

    return delta

class NLPDateRange(object):
    """docstring for NLPDate"""
    def __init__(self, dtn=None):
        super(NLPDateRange, self).__init__()

        self.keyword = {
            'yesterday' : (1, 'day'),
            'today'     : (0, 'day'),
            'this'      : 0,
            'last'      : 1,
            'next'      :-1,
        }

        base_unit = ['hour','day','week','month','year']

        rex_units = '('+'|'.join(base_unit)+')s?'
        rex_words = '('+"today|yesterday|" + ')'
        rex_mod   = '(\d+|next|this|last)'
        rex_ago   = '(?:\s+ago)?'
        rex_to    = '(?:to|til)'
        rex_modv  = rex_mod+'\s+'+rex_units

        # http://www.regexper.com/
        rex_format = '^(?:last\s+)?(?:'+rex_words+'|'+rex_modv+')'+rex_ago+ \
                     '(?:(?:\s+'+rex_to+'\s+'+rex_words+')?|\s+'+ \
                     rex_to+'\s+'+rex_modv+rex_ago+')$'

        self.match_words = re.compile(rex_format)

        if dtn is None:
            self.dtn = datetime.datetime.now()
        else:
            self.dtn = dtn


    def parse(self,text):

        # nlp naturally tries to parse language of past dates and ranges

        # negative flips the default range of
        #   from date to today
        # to:
        #   from -infinity to date
        negative=False
        if text.startswith("older than"):
            text = text.replace('older than','').strip()
            negative = True

        m = self.match_words.match(text)
        if m:
            g= m.groups()

            if not any(g):
                return

            range_start = g[1:3] if all(g[1:3]) else g[0]
            range_end   = g[4: ] if all(g[4: ]) else g[3]
            range_start = self.keyword.get(range_start,range_start)
            range_end   = self.keyword.get(range_end  ,range_end  )

            if range_start:
                srng = -int(self.keyword.get(range_start[0],range_start[0]))
                range_start= (srng,range_start[1])
            if range_end:
                srng = -int(self.keyword.get(range_end[0],  range_end[0]))
                range_end  = (srng, range_end[1])

            #print g
            if not range_end: # shifts range to that of one unit
                range_end = range_start # (-1,range_start[1])

            if negative: # shift the time search from infinity to some day
                range_start = (-100,'year') # (-1,range_start[1])

            # get the datetime object for year (count,unit) from today
            ds=unit_start(self.dtn,*range_start)
            de=unit_start(self.dtn,*range_end)

            if not negative: # add one unit to the end range
                de = de + unit_delta(de,range_end[1])
            return ds,de
        return None

def main():

    samples = []
    samples.append('today')
    samples.append('this hour')
    samples.append('last week')
    samples.append('last month')
    samples.append('this month')

    samples.append('last week to today')
    samples.append('last week to 4 days ago')
    samples.append('12 weeks ago to 4 days ago')
    samples.append('12 weeks ago to today')
    samples.append('this hour')
    samples.append('last 10 weeks til yesterday')
    samples.append('2 weeks ago to next hour')
    samples.append('older than yesterday')
    samples.append('older than last month')
    samples.append('older than 3 weeks ago')
    samples.append('4 hours ago')
    samples.append('4 days ago til 2 days ago')
    samples.append('')

    #print match_words.pattern
    nlp = NLPDateRange()
    for text in samples:
        #print text,
        result = nlp.parse(text)
        if result:
            ds,de = result
            t1 = timegm(ds.utctimetuple())
            t2 = timegm(de.utctimetuple())
            print(ds, de, t1, t2, text)
            #print ppdt(ds),'-->',ppdt(de)
            #print timegm(de.utctimetuple()), (de-ds).total_seconds()
        else:
            #print "error"
            pass

if __name__ == '__main__':
    main()