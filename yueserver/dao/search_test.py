#! cd ../.. && python setup.py test
#! C:\\Python35\\python.exe $this

"""
todo: none of these tests actually check that the correct answer is returned,
only that the answers for applying rules, vs using sql match.
"""

import unittest
import os
import sys
import datetime
import calendar
import traceback
import time

from sqlalchemy import column, select
from sqlalchemy.schema import Table, Column
from sqlalchemy.types import Integer, String

from .tables.util import generate_uuid
from .db import main_test, db_connect_test
from .user import UserDao
from .library import Song, LibraryDao

from .search import SearchGrammar, \
        FormatConversion, \
        PartialStringSearchRule, \
        InvertedPartialStringSearchRule, \
        ExactSearchRule, \
        InvertedExactSearchRule, \
        LessThanSearchRule, \
        LessThanEqualSearchRule, \
        GreaterThanSearchRule, \
        GreaterThanEqualSearchRule, \
        RegExpSearchRule, \
        RangeSearchRule, \
        NotRangeSearchRule, \
        NotSearchRule, \
        AndSearchRule, \
        OrSearchRule, \
        MultiColumnSearchRule, \
        Rule, \
        BlankSearchRule, \
        naive_search, \
        ParseError, \
        RHSError, \
        LHSError, \
        StrPos, \
        naive_search

def extract(field, items):
    return set(item[field] for item in items)

# TODO: manage drop does not clean up this table
# move this class somewhere else so that it can
def TestSongTable(metadata):

    return Table('test_song_data', metadata,
        Column('id', String, primary_key=True, default=generate_uuid),
        # string
        Column('artist', String),
        Column('album', String),
        Column('title', String),
        Column('file_path', String),
        # number
        Column('play_count', Integer, default=0),
        # time
        Column('length', Integer, default=0),
        # year
        Column('year', Integer, default=0),
        # date
        Column('date', Integer, default=lambda: int(time.time()))
    )

def db_insert(db, table, items):

    uids = []
    for item in items:
        query = table.insert().values(item)
        result = db.session.execute(query)
        uid = result.inserted_primary_key[0]
        uids.append(uid)

    db.session.commit()
    return uids

def db_select(db, table, rule, columns=[]):
    rule = rule.psql() if db.kind() == "postgresql" else rule.sql()
    if not columns:
        columns = [c.name for c in table.c]
    query = select([column(c) for c in columns]).select_from(table).where(rule)

    results = db.session.execute(query).fetchall()

    return [{k: v for k, v in zip(columns, item)} for item in results]

class TestSearchMeta(type):
    """
    Build a Search Test class.
    search test follow a forumla, compare output from two different search
    methods. This class builds a Test Class where each method in the class
    runs the same test with different parameters

    """
    def __new__(cls, name, bases, attr):

        def gen_compare_test(rule):
            """ check that a given rule returns the same results,
                using the sql expression, or directly applying the rule """
            def test(self):
                s1 = extract( Song.id, naive_search( self.SONGS, rule) )
                s2 = extract( Song.id, db_select(
                    self.db, self.db.tables.TestSongTable, rule) )
                m = "\nrule: %s\ns1(naive): %s\ns2( sql ):%s\n"%(rule,s1,s2)
                self.assertEqual(s1,s2,m)
            return test

        def gen_compare_count_test(rule,count):
            """ check that a rule returns the expected number of results"""
            def test(self):
                s1 = extract( Song.id, db_select(
                    self.db, self.db.tables.TestSongTable, rule) )
                self.assertEqual(len(s1), count)
            return test

        def gen_compare_rule_test(rule1,rule2):
            """ check that two different rules return the same results """
            def test(self):
                r1 = db_select(
                    self.db, self.db.tables.TestSongTable, rule1)
                r2 = db_select(
                    self.db, self.db.tables.TestSongTable, rule2)
                s1 = extract(Song.id, r1)
                s2 = extract(Song.id, r2)
                a1 = ", ".join(sorted(extract(Song.artist, r1)))
                a2 = ", ".join(sorted(extract(Song.artist, r2)))
                self.assertEqual(s1, s2, "\n%s\n%s" % (a1, a2))
            return test

        rng1 = RangeSearchRule(column('play_count'),1995,2005,type_=int)
        rng2 = NotRangeSearchRule(column('play_count'),1995,2005,type_=int)

        # show that two rules combined using 'and' produce the expected result
        gt1=GreaterThanEqualSearchRule(column('play_count'),1995,type_=int)
        lt1=LessThanEqualSearchRule(column('play_count'),2005,type_=int)

        # show that two rules combined using 'or' produce the correct result
        lt2=LessThanSearchRule(column('play_count'),1995,type_=int)
        gt2=GreaterThanSearchRule(column('play_count'),2005,type_=int)

        pl1 = PartialStringSearchRule(column('artist'),'art1')
        pl2 = InvertedPartialStringSearchRule(column('artist'),'art1')

        rex1 = RegExpSearchRule(column('artist'), "^art1.*$")
        rex_cmp = PartialStringSearchRule(column('artist'), "art1")

        and1 = AndSearchRule([gt1,lt1])
        or1 = OrSearchRule([lt2,gt2])

        not1 = NotSearchRule([rng1,])
        rules = [ pl1,
                  pl2,
                  ExactSearchRule(column('artist'),'art1'),
                  ExactSearchRule(column('play_count'),2000,type_=int),
                  InvertedExactSearchRule(column('artist'),'art1'),
                  InvertedExactSearchRule(column('play_count'),2000,type_=int),
                  rng1, rng2, gt1, gt2, lt1, lt2, and1, or1, not1, rex1
                  ]

        for i, rule in enumerate(rules):
            test_name = "test_rule_%d" % i
            attr[test_name] = gen_compare_test(rule)

        attr["test_and"] = gen_compare_rule_test(and1, rng1)
        attr["test_or"] = gen_compare_rule_test(or1, rng2)
        attr["test_rng"] = gen_compare_rule_test(rng2, not1)
        attr["test_rex1"] = gen_compare_rule_test(rex1, rex_cmp)

        attr["test_pl1"] = gen_compare_count_test(pl1,11)
        attr["test_pl2"] = gen_compare_count_test(pl2, 9)

        return super(TestSearchMeta,cls).__new__(cls, name, bases, attr)

class SearchOperatorTestCase(unittest.TestCase, metaclass=TestSearchMeta):

    @classmethod
    def setUpClass(cls):

        db = db_connect_test(cls.__name__)
        db.tables.TestSongTable = TestSongTable(db.metadata)
        db.tables.TestSongTable.drop(db.engine, checkfirst=True)
        db.create_all()

        cls.SONGS = []
        for i in range(20):
            song = {Song.artist:"art%d"%i,
                    Song.album :"alb%d"%i,
                    Song.title :"ttl%d"%i,
                    Song.path  :"/path/%d"%i,
                    Song.play_count:i,
                    Song.year:i%21+1990}
            cls.SONGS.append(song)

        cls.SONGIDS = db_insert(db, db.tables.TestSongTable, cls.SONGS)
        for song, song_id in zip(cls.SONGS, cls.SONGIDS):
            song[Song.id] = song_id

        cls.db = db

    def test_join_and(self):

        r = Rule()

        t1 = AndSearchRule.join()
        t2 = AndSearchRule.join(r)
        t3 = AndSearchRule.join(r, r)

        self.assertTrue(isinstance(t1, BlankSearchRule))
        self.assertTrue(t2 is r, t2)
        self.assertTrue(isinstance(t3, AndSearchRule))
        self.assertTrue(t3.rules[0] is r)
        self.assertTrue(t3.rules[1] is r)

    def test_join_or(self):

        r = Rule()

        t1 = OrSearchRule.join()
        t2 = OrSearchRule.join(r)
        t3 = OrSearchRule.join(r, r)

        self.assertTrue(isinstance(t1, BlankSearchRule))
        self.assertTrue(t2 is r, t2)
        self.assertTrue(isinstance(t3, OrSearchRule))
        self.assertTrue(t3.rules[0] is r)
        self.assertTrue(t3.rules[1] is r)

class SearchGrammarTestCase(unittest.TestCase):
    """
    """
    def __init__(self,*args,**kwargs):
        super(SearchGrammarTestCase,self).__init__(*args,**kwargs)

    def setUp(self):

        self.dtn = datetime.datetime(2018,3,12)
        self.sg = SearchGrammar(self.dtn);

        self.sg.autoset_datetime = False
        self.sg.text_fields = ["value1", "value2"]
        self.sg.date_fields = ["date", ]
        self.sg.year_fields = ["year", ]
        self.sg.time_fields = ["elapsed", ]
        self.sg.number_fields = ["count", ]

    def tearDown(self):
        pass

    def test_date_delta(self):

        dtn = datetime.datetime(2015,6,15)
        fc = FormatConversion( dtn );

        # show that we can subtract one month and one year from a date
        dt = fc.computeDateDelta(dtn.year,dtn.month,dtn.day,1,1)
        self.assertEqual(dt.year,dtn.year-1)
        self.assertEqual(dt.month,dtn.month-1)
        self.assertEqual(dt.day,dtn.day)

        # there is no february 31st, so the month is incremented
        # to get the day value to agree
        dt = fc.computeDateDelta(2015,3,31,0,1)
        self.assertEqual(dt.year ,2015)
        self.assertEqual(dt.month,3)
        self.assertEqual(dt.day  ,3)

        # december is a special case, and subtracting (0,0) uncovered it.
        dt = fc.computeDateDelta(2016,12,1,0,0)
        self.assertEqual(dt.year ,2016)
        self.assertEqual(dt.month,12)
        self.assertEqual(dt.day  ,1)

        dt = fc.computeDateDelta(2016,11,1,1,0)
        self.assertEqual(dt.year ,2015)
        self.assertEqual(dt.month,11)
        self.assertEqual(dt.day  ,1)

        dt = fc.computeDateDelta(2017,2,1,0,2) # 0 month bug
        self.assertEqual(dt.year ,2016)
        self.assertEqual(dt.month,12)
        self.assertEqual(dt.day  ,1)

        dt = fc.computeDateDelta(2017,2,15,0,1,15) # check delta day
        self.assertEqual(dt.year ,2016)
        self.assertEqual(dt.month,12)
        self.assertEqual(dt.day  ,31)

        dt = fc.computeDateDelta(2017,12,32,0,0,0) # check delta day
        self.assertEqual(dt.year ,2018)
        self.assertEqual(dt.month,1)
        self.assertEqual(dt.day  ,1)

    def test_format_date_delta(self):

        dtn = datetime.datetime(2015,6,15)
        fc = FormatConversion( dtn );

        t1,t2 = fc.formatDateDelta("1")
        dt = datetime.datetime(dtn.year,dtn.month,dtn.day-1)
        self.assertEqual(t1,calendar.timegm(dt.timetuple()))

        t1,t2 = fc.formatDateDelta("1d")
        dt = datetime.datetime(dtn.year,dtn.month,dtn.day-1)
        self.assertEqual(t1,calendar.timegm(dt.timetuple()))

        t1,t2 = fc.formatDateDelta("-1d")
        dt = datetime.datetime(dtn.year,dtn.month,dtn.day+1)
        self.assertEqual(t1,calendar.timegm(dt.timetuple()))

        t1,t2 = fc.formatDateDelta("1y1m1w1d")
        dt = datetime.datetime(dtn.year-1,dtn.month-1,dtn.day-8)
        self.assertEqual(t1,calendar.timegm(dt.timetuple()))

    def test_date_format(self):

        dtn = self.sg.fc.datetime_now = datetime.datetime(2015,6,15);
        self.sg.autoset_datetime = False

        t1,t2 = self.sg.fc.formatDate("15")
        self.assertEqual(t1,calendar.timegm(datetime.datetime(2015,1,1).timetuple()))

        t1,t2 = self.sg.fc.formatDate("2015")
        self.assertEqual(t1,calendar.timegm(datetime.datetime(2015,1,1).timetuple()))

        t1,t2 = self.sg.fc.formatDate("2015/6")
        self.assertEqual(t1,calendar.timegm(datetime.datetime(2015,6,1).timetuple()))

        t1,t2 = self.sg.fc.formatDate("15/06/")
        self.assertEqual(t1,calendar.timegm(datetime.datetime(2015,6,1).timetuple()))

        t1,t2 = self.sg.fc.formatDate("2015/6/15")
        self.assertEqual(t1,calendar.timegm(datetime.datetime(2015,6,15).timetuple()))

        t1,t2 = self.sg.fc.formatDate("15/06/15")
        self.assertEqual(t1,calendar.timegm(datetime.datetime(2015,6,15).timetuple()))

        t1,t2 = self.sg.fc.formatDate("75/06/15")
        self.assertEqual(t1,calendar.timegm(datetime.datetime(1975,6,15).timetuple()))

        # todo: may want to delete the code that handles this case
        with self.assertRaises(ParseError):
            self.sg.fc.formatDate(StrPos("1776",0,4))

        with self.assertRaises(ParseError):
            self.sg.fc.formatDate(StrPos("1776/1",0,6))

    def test_parse_duration(self):

        t = self.sg.fc.parseDuration(StrPos("35",0,6))
        self.assertEqual(t, 35)

        t = self.sg.fc.parseDuration(StrPos("90",0,6))
        self.assertEqual(t, 90)

        t = self.sg.fc.parseDuration(StrPos("1:30",0,6))
        self.assertEqual(t, 90)

        with self.assertRaises(ParseError):
            t = self.sg.fc.parseDuration(StrPos("3.5",0,6))

        t = self.sg.fc.parseYear(StrPos("15",0,6))
        self.assertEqual(t, 2015)

        t = self.sg.fc.parseYear(StrPos("1900",0,6))
        self.assertEqual(t, 1900)

        with self.assertRaises(ParseError):
            t = self.sg.fc.parseYear(StrPos("12.5",0,6))

    def test_nlp(self):

        dtn = datetime.datetime(2015,6,15)
        fc = FormatConversion( dtn );

        t1, t2 = fc.parseNLPDate(StrPos("today",0,6))
        self.assertEqual(t1,calendar.timegm(datetime.datetime(2015,6,15).timetuple()))
        self.assertEqual(t2,calendar.timegm(datetime.datetime(2015,6,16).timetuple()))

        t1, t2 = fc.parseNLPDate(StrPos("older than last month",0,6))
        self.assertEqual(t1,0)
        self.assertEqual(t2,calendar.timegm(datetime.datetime(2015,5,1).timetuple()))

    def test_tokenize(self):


        t = self.sg.tokenizeString(" \\a ")
        self.assertEqual(t[0], "a")

        t = self.sg.tokenizeString("value1 = \"abc\"")
        self.assertEqual(t[-1], "abc")

    def test_rulegen_parse(self):

        r = self.sg.ruleFromString("count > 1 && count<3")
        self.assertTrue(isinstance(r, AndSearchRule), type(r))
        a,b = r.rules
        self.assertTrue(isinstance(a, GreaterThanSearchRule), type(a))
        self.assertTrue(isinstance(b, LessThanSearchRule), type(b))
        self.assertEqual(a.value, '1')
        self.assertEqual(b.value, '3')

        r = self.sg.ruleFromString("value1 = \"abc\"")
        self.assertTrue(isinstance(a, PartialStringSearchRule), type(a))
        self.assertEqual(r.value, 'abc')

        # quote and escape quotes inside
        r = self.sg.ruleFromString("value1 = \"\\\"abc\\\"\"")
        self.assertTrue(isinstance(a, PartialStringSearchRule), type(a))
        self.assertEqual(r.value, '"abc"')

        # escape the quotes themselves
        r = self.sg.ruleFromString("value1 = \\\"abc\\\"")
        self.assertTrue(isinstance(a, PartialStringSearchRule), type(a))
        self.assertEqual(r.value, '"abc"')

        r = self.sg.ruleFromString("()")
        self.assertTrue(isinstance(r, BlankSearchRule))

    def test_rulegen_date_grammer(self):

        dtn = self.dtn

        r = self.sg.ruleFromString("date = today")
        self.assertTrue(isinstance(r, RangeSearchRule), type(r))
        dt1 = datetime.datetime(dtn.year,dtn.month,dtn.day)
        dt2 = datetime.datetime(dtn.year,dtn.month,dtn.day+1)
        self.assertEqual(r.value_low,calendar.timegm(dt1.timetuple()))
        self.assertEqual(r.value_high,calendar.timegm(dt2.timetuple()))

        r2 = self.sg.ruleFromString("(date = today)")
        self.assertEqual(str(r), str(r2))

    def test_rulegen_parse(self):

        with self.assertRaises(RHSError):
            self.sg.ruleFromString("count >")

        with self.assertRaises(RHSError):
            self.sg.ruleFromString("count > >")

        with self.assertRaises(RHSError):
            self.sg.ruleFromString("count > &&")

        with self.assertRaises(RHSError):
            self.sg.ruleFromString("count > 1 &&")

        with self.assertRaises(RHSError):
            self.sg.ruleFromString("count > 0 && ()")

        with self.assertRaises(LHSError):
            self.sg.ruleFromString("> 1")

        with self.assertRaises(LHSError):
            self.sg.ruleFromString("&& count > 1")

        # illegal operator
        with self.assertRaises(ParseError):
            self.sg.ruleFromString("count <> 1")

        # unknown column
        with self.assertRaises(ParseError):
            self.sg.ruleFromString("dne <> 1")

        # escape character at end of input
        with self.assertRaises(ParseError):
            self.sg.ruleFromString("\\")

        with self.assertRaises(RHSError):
            self.sg.parseTokens([StrPos("count", 0, 0),
                                 StrPos("=", 0, 0)])

        with self.assertRaises(RHSError):
            r = self.sg.parseTokens([StrPos("count", 0, 0),
                                 StrPos("=", 0, 0),
                                 StrPos("&&", 0, 0, "special")])

    def test_rulegen_alltext(self):

        r = self.sg.ruleFromString(" = this")
        self.assertTrue(isinstance(r, MultiColumnSearchRule))
        self.assertTrue(all([c in self.sg.text_fields for c in r.columns]))

        # show that the default parameter is interpretted
        r = self.sg.ruleFromString("count=1 =this")
        self.assertTrue(isinstance(r, AndSearchRule), type(r))
        self.assertEqual(r.rules[-1].colid, "text")

        r = self.sg.ruleFromString("(count=0 || count=1) = this")
        self.assertTrue(isinstance(r, AndSearchRule), type(r))
        self.assertEqual(r.rules[-1].colid, "text")

    def test_rulegen_negate(self):

        r = self.sg.ruleFromString("! count=1")
        self.assertTrue(isinstance(r, NotSearchRule), type(r))

    def test_rulegen_meta(self):
        r = self.sg.ruleFromString("limit=5 count=1")
        self.assertTrue(isinstance(r, ExactSearchRule), type(r))
        self.assertEqual(self.sg.meta_options['limit'], 5)

        r = self.sg.ruleFromString("debug=0 count=1")
        self.assertEqual(self.sg.meta_options['debug'], 0)

        with self.assertRaises(ParseError):
            self.sg.ruleFromString("(debug=0) count=1")

        with self.assertRaises(ParseError):
            self.sg.ruleFromString("debug=0 debug=1")

class SearchTestCase(unittest.TestCase):
    """
    """
    def __init__(self,*args,**kwargs):
        super(SearchTestCase,self).__init__(*args,**kwargs)

    def setUp(self):

        self.dtn = datetime.datetime(2018,3,12)
        self.sg = SearchGrammar(self.dtn);

        self.sg.autoset_datetime = False
        self.sg.text_fields = ["value1", "value2"]
        self.sg.date_fields = ["date", ]
        self.sg.year_fields = ["year", ]
        self.sg.time_fields = ["elapsed", ]
        self.sg.number_fields = ["count", ]

    def tearDown(self):
        pass

    def test_naive_search(self):

        items = [{"number": 0,}, {"number": 9,}]
        rule = LessThanSearchRule(StrPos("number", 0, 0), 5)

        result = naive_search(items, rule)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['number'], 0)

    def test_naive_search(self):

        items = [{"number": 0,}, {"number": 9,}]
        rule = LessThanSearchRule(StrPos("number", 0, 0), 5)

        result = naive_search(items, BlankSearchRule())

        self.assertEqual(len(result), 2)

    def test_naive_search_order(self):
        # the orderby kwarg should control the order of returned elements

        items=[{"number": i,} for i in range(10)]
        rule = LessThanSearchRule(StrPos("number", 0, 0), 5)

        result = naive_search(items, rule, orderby="number")
        self.assertEqual(len(result), 5)
        for i in range(1, len(result)):
            self.assertEqual(result[i-1]['number'], result[i]['number']-1)

        result = naive_search(items, rule, orderby=["number"])
        self.assertEqual(len(result), 5)
        for i in range(1, len(result)):
            self.assertEqual(result[i-1]['number'], result[i]['number']-1)

        result = naive_search(items, rule, orderby=[("number", "ASC")])
        self.assertEqual(len(result), 5)
        for i in range(1, len(result)):
            self.assertEqual(result[i-1]['number'], result[i]['number']-1)

        result = naive_search(items, rule, orderby=[("number", "DESC")])
        self.assertEqual(len(result), 5)
        for i in reversed(range(1, len(result))):
            self.assertEqual(result[i-1]['number'], result[i]['number']+1)

    def test_naive_search_columns(self):
        # the columns kwarg should filter results to only return the named keys

        items = [{"number": 0, "string": "a"}, {"number": 9, "string": "b"}]

        rule = LessThanSearchRule(StrPos("number", 0, 0), 5)
        result = naive_search(items, rule, columns=['string'])
        self.assertEqual(len(result), 1)
        self.assertTrue("string" in result[0], "a")
        self.assertTrue("number" not in result[0], "a")
        self.assertEqual(result[0]['string'], "a")

    def test_naive_search_limit(self):
        items=[{"number": i,} for i in range(10)]
        rule = LessThanSearchRule(StrPos("number", 0, 0), 5)

        result = naive_search(items, rule, orderby="number", offset=1, limit=2)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['number'], 1)
        self.assertEqual(result[1]['number'], 2)

    def test_naive_search_meta(self):
        # the orderby kwarg should control the order of returned elements

        items=[{"number": i,} for i in range(10)]
        rulea = LessThanSearchRule(StrPos("number", 0, 0), 8)
        ruleb = GreaterThanSearchRule(StrPos("number", 0, 0), 2)
        rule = AndSearchRule([rulea, ruleb])
        result = naive_search(items, rule)
        for r in result:
            self.assertTrue(r['number'] > 2)
            self.assertTrue(r['number'] < 8)

    def test_rule(self):

        rulea = LessThanSearchRule(StrPos("number", 0, 0), 8)
        ruleb = GreaterThanSearchRule(StrPos("number", 0, 0), 2)

        self.assertEqual(rulea, rulea)
        self.assertNotEqual(rulea, ruleb)

if __name__ == '__main__':
    main_test(sys.argv, globals())

