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

from .db import db_init_main, db_connect
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
        StrPos

def extract(field, items):
    return set( item[field] for item in items )

class TestSearchMeta(type):
    """
    Build a Search Test class.
    search test follow a forumla, compare output from two different search
    methods. This class builds a Test Class where each method in the class
    runs the same test with different parameters

    """
    def __new__(cls, name, bases, attr):

        db = db_connect(None)

        env_cfg = {
            'features': ['test', ],
            'domains': ['test'],
            'roles': [
                {'test': { 'features': ['all',]}},
            ],
            'users': [
                {'email': 'user000',
                 'password': 'user000',
                 'domains': ['test'],
                 'roles': ['test']},
                {'email': 'user001',
                 'password': 'user001',
                 'domains': ['test'],
                 'roles': ['test']},
                {'email': 'user002',
                 'password': 'user002',
                 'domains': ['test'],
                 'roles': ['test']},
            ]
        }

        db_init_main(db, db.tables, env_cfg)

        cls.userDao = UserDao(db, db.tables)

        cls.USERNAME = "user000"
        cls.USER = cls.userDao.findUserByEmail(cls.USERNAME)

        cls.libraryDao = LibraryDao(db, db.tables)

        cls.SONGS = []
        for i in range(20):
            song = {Song.artist:"art%d"%i,
                    Song.album :"alb%d"%i,
                    Song.title :"ttl%d"%i,
                    Song.path  :"/path/%d"%i,
                    Song.play_count:i,
                    Song.year:i%21+1990}
            id = cls.libraryDao.insert(cls.USER["id"], cls.USER["domain_id"], song)
            song[Song.id] = id
            cls.SONGS.append(song)

        cls.db = db

        attr['db'] = cls.db
        attr['SONGS'] = cls.SONGS
        attr['libraryDao'] = cls.libraryDao
        attr['libraryDao'] = cls.libraryDao
        attr['USERNAME'] = cls.USERNAME
        attr['USER'] = cls.USER


        def gen_compare_test(rule):
            """ check that a given rule returns the same results,
                using the sql expression, or directly applying the rule """
            def test(self):
                s1 = extract( Song.id, naive_search( self.SONGS, rule) )
                s2 = extract( Song.id, self.libraryDao.search(
                    self.USER["id"], self.USER["domain_id"], rule) )
                m = "\nrule: %s\ns1(naive): %s\ns2( sql ):%s\n"%(rule,s1,s2)
                self.assertEqual(s1,s2,m)
            return test

        def gen_compare_count_test(rule,count):
            """ check that a rule returns the expected number of results"""
            def test(self):
                s1 = extract( Song.id, self.libraryDao.search(
                    self.USER["id"], self.USER["domain_id"], rule) )
                self.assertEqual(len(s1), count)
            return test

        def gen_compare_rule_test(rule1,rule2):
            """ check that two different rules return the same results """
            def test(self):
                r1 = self.libraryDao.search(
                    self.USER["id"], self.USER["domain_id"], rule1)
                r2 = self.libraryDao.search(
                    self.USER["id"], self.USER["domain_id"], rule2)
                s1 = extract(Song.id, r1)
                s2 = extract(Song.id, r2)
                a1 = ", ".join(sorted(extract(Song.artist, r1)))
                a2 = ", ".join(sorted(extract(Song.artist, r2)))
                self.assertEqual(s1, s2, "\n%s\n%s" % (a1, a2))
            return test

        c = lambda col:cls.libraryDao.grammar.getColumnType(col)

        rng1 = RangeSearchRule(c('play_count'),1995,2005,type_=int)
        rng2 = NotRangeSearchRule(c('play_count'),1995,2005,type_=int)

        # show that two rules combined using 'and' produce the expected result
        gt1=GreaterThanEqualSearchRule(c('play_count'),1995,type_=int)
        lt1=LessThanEqualSearchRule(c('play_count'),2005,type_=int)

        # show that two rules combined using 'or' produce the correct result
        lt2=LessThanSearchRule(c('play_count'),1995,type_=int)
        gt2=GreaterThanSearchRule(c('play_count'),2005,type_=int)

        pl1 = PartialStringSearchRule(c('artist'),'art1')
        pl2 = InvertedPartialStringSearchRule(c('artist'),'art1')

        rex1 = RegExpSearchRule(c('artist'), "^art1.*$")
        rex_cmp = PartialStringSearchRule(c('artist'), "art1")

        and1 = AndSearchRule([gt1,lt1])
        or1 = OrSearchRule([lt2,gt2])

        not1 = NotSearchRule([rng1,])
        rules = [ pl1,
                  pl2,
                  ExactSearchRule(c('artist'),'art1'),
                  ExactSearchRule(c('play_count'),2000,type_=int),
                  InvertedExactSearchRule(c('artist'),'art1'),
                  InvertedExactSearchRule(c('play_count'),2000,type_=int),
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

class SearchTestCase(unittest.TestCase, metaclass=TestSearchMeta):


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

    def test_rulegen_alltext(self):

        r = self.sg.ruleFromString(" = this")
        self.assertTrue(isinstance(r, MultiColumnSearchRule))
        self.assertTrue(all([c in self.sg.text_fields for c in r.columns]))


def main():
    suite = unittest.TestSuite()

    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(SearchTestCase))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(SearchGrammarTestCase))

    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()

