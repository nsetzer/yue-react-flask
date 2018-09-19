
"""
Implements a grammar for querying a SQL-like database

Both a flat array of elements or a database may be queried
using a common grammar
"""
from .nlpdatesearch import NLPDateRange

from .util import format_delta, format_date, string_quote
import re
import calendar
from datetime import datetime, timedelta
import time

from sqlalchemy import and_, or_, not_, select, between

import sys

class IntDate(int):
    """ integer tagged as an epoch-time, see SearchRule.fmtval()"""
    def __new__(cls, *args, **kwargs):
        return super(IntDate, cls).__new__(cls, args[0])

class IntTime(int):
    """ integer tagged as a time delta, see SearchRule.fmtval()"""
    def __new__(cls, *args, **kwargs):
        return super(IntTime, cls).__new__(cls, args[0])

class StrPos(str):
    """ A string tagged with a position value"""
    def __new__(cls, strval, pos, end, kind="text"):
        inst = super(StrPos, cls).__new__(cls, strval)
        inst.pos = pos
        inst.end = end
        inst.kind = kind
        inst.name = strval
        return inst

class Rule(object):

    def __init__(self):
        super(Rule, self).__init__()

    def __eq__(self, othr):
        return repr(self) == repr(othr)

    def sql(self):
        """ return SQLite3 representation of this string
            the string should have question marks (?) in place
            of the values, which will be filled in when the sql
            is executed.
            each value in the returned list of values should
            correspond with 1 question mark, from left to right.

            see sqlstr()
        """
        raise NotImplementedError()

    def psql(self):
        """ return PostgresSQL representation of this rule
        """
        return self.sql()

    def __repr__(self):
        return "<%s>" % self.__class__.__name__

    def fmtval(self, v):
        if isinstance(v, IntDate):
            return string_quote(format_date(v))
        elif isinstance(v, IntTime):
            return string_quote(format_delta(v))
        elif isinstance(v, str):
            return string_quote(v)
        return v

    def sqlstr(self):
        raise NotImplementedError()

class SearchRule(Rule):
    """Baseclass for search rules

    The check()/sql() methods are a form of self documentation and are
    database implementation dependent. For example the check method
    for the RangeSearchRule rule is implemented to match the BETWEEN condition
    in sqlite3.

    """

    def __init__(self):
        super(SearchRule, self).__init__()

    def check(self, elem, ignoreCase=True):
        raise NotImplementedError(self.__class__.__name__)

    def sqlstr(self):
        """ like sql() but returns a single string representing the rule"""
        s, v = self.sql()
        return s.replace("?", "{}").format(*map(self.fmtval, v))

class BlankSearchRule(SearchRule):
    """a rule that matches all values"""

    def check(self, elem, ignoreCase=True):
        return True

    def sql(self):
        return None

    def __repr__(self):
        return "<all>"

    def sqlstr(self):
        return ""

class ColumnSearchRule(SearchRule):
    """Base class for applying a rule to a column in a table"""

    def __init__(self, column, value, type_=str):
        super(SearchRule, self).__init__()
        self.column = column
        self.value = value
        self.type_ = type_

def rexcmp(expr):
    return re.compile(expr, re.IGNORECASE)

def regexp(expr, item):
    reg = rexcmp(expr)
    return reg.search(item) is not None

def case_(string, lower):
    if lower and hasattr(string, "lower"):
        return string.lower()
    return string

class RegExpSearchRule(ColumnSearchRule):
    """matches a value using a regular expression"""

    def __init__(self, column, value, type_=str):
        super(RegExpSearchRule, self).__init__(column, value, type_)

        # test that this regular expression can compile
        # note that column, value are StrPos and we can determine
        # precisely where the error occurred.
        try:
            rexcmp(value)
        except re.error as e:
            msg = "Regular Expression Error: %s at position %d in `%s`" % (e.msg, e.colno, value)
            raise ParseError(msg)

    def check(self, elem, ignoreCase=True):
        return regexp(self.value, elem[self.column.name])

    def __repr__(self):
        return "<%s =~ %s>" % (self.column, self.fmtval(self.value))

    def sql(self):
        return self.column.op("REGEXP")(self.value)

    def psql(self):
        return self.column.op("~")(self.value)

class PartialStringSearchRule(ColumnSearchRule):
    """matches if a value contains the given text"""

    def check(self, elem, ignoreCase=True):
        v1 = self.type_(case_(self.value, ignoreCase))
        v2 = self.type_(case_(elem[self.column.name], ignoreCase))
        return v1 in v2

    def __repr__(self):
        return "<%s in `%s`>" % (self.fmtval(self.value), self.column)

    def sql(self):
        return self.column.ilike("%%%s%%" % self.value)

class InvertedPartialStringSearchRule(ColumnSearchRule):
    """does not match if a value contains the given text"""

    def check(self, elem, ignoreCase=True):
        v1 = self.type_(case_(self.value, ignoreCase))
        v2 = self.type_(case_(elem[self.column.name], ignoreCase))
        return v1 not in v2

    def __repr__(self):
        return "<%s not in `%s`>" % (self.fmtval(self.value), self.column)

    def sql(self):
        return self.column.notilike("%%%s%%" % self.value)

class ExactSearchRule(ColumnSearchRule):
    """matches if the a value is exactly equal to the given

    this works for text or integers
    """

    def check(self, elem, ignoreCase=True):
        v1 = self.type_(case_(self.value, ignoreCase))
        v2 = self.type_(case_(elem[self.column.name], ignoreCase))
        return v1 == v2

    def __repr__(self):
        return "<%s == %s>" % (self.column, self.fmtval(self.value))

    def sql(self):
        return self.column.op("=")(self.value)

class InvertedExactSearchRule(ColumnSearchRule):
    """matches as long as the value does not exactly equal the given"""

    def check(self, elem, ignoreCase=True):
        v1 = self.type_(case_(self.value, ignoreCase))
        v2 = self.type_(case_(elem[self.column.name], ignoreCase))
        return v1 != v2

    def __repr__(self):
        return "<%s != %s>" % (self.column, self.fmtval(self.value))

    def sql(self):
        return self.column.op("!=")(self.value)

class LessThanSearchRule(ColumnSearchRule):
    """matches as long as the value is less than the given number"""

    def check(self, elem, ignoreCase=True):
        v1 = self.type_(case_(self.value, ignoreCase))
        v2 = self.type_(case_(elem[self.column.name], ignoreCase))
        return v2 < v1

    def __repr__(self):
        return "<%s < %s>" % (self.column, self.fmtval(self.value))

    def sql(self):
        return self.column.op("<")(self.value)

class LessThanEqualSearchRule(ColumnSearchRule):
    """matches as long as the value is less than or equal to the given number"""

    def check(self, elem, ignoreCase=True):
        v1 = self.type_(case_(self.value, ignoreCase))
        v2 = self.type_(case_(elem[self.column.name], ignoreCase))
        return v2 <= v1

    def __repr__(self):
        return "<%s <= %s>" % (self.column, self.fmtval(self.value))

    def sql(self):
        return self.column.op("<=")(self.value)

class GreaterThanSearchRule(ColumnSearchRule):
    """matches as long as the value is greater than the given number"""

    def check(self, elem, ignoreCase=True):
        v1 = self.type_(case_(self.value, ignoreCase))
        v2 = self.type_(case_(elem[self.column.name], ignoreCase))
        return v2 > v1

    def __repr__(self):
        return "<%s > %s>" % (self.column, self.fmtval(self.value))

    def sql(self):
        return self.column.op(">")(self.value)

class GreaterThanEqualSearchRule(ColumnSearchRule):
    """matches as long as the value is greater than or equal to the given number"""

    def check(self, elem, ignoreCase=True):
        v1 = self.type_(case_(self.value, ignoreCase))
        v2 = self.type_(case_(elem[self.column.name], ignoreCase))
        return v2 >= v1

    def __repr__(self):
        return "<%s >= %s>" % (self.column, self.fmtval(self.value))

    def sql(self):
        return self.column.op(">=")(self.value)

class RangeSearchRule(SearchRule):
    """matches if a value is within a rage of values
    sqlite3: values are inclusive on the range specified
    """

    def __init__(self, column, value_low, value_high, type_=str):
        super(RangeSearchRule, self).__init__()
        self.column = column
        self.value_low = value_low
        self.value_high = value_high
        self.type_ = type_

    def check(self, elem, ignoreCase=True):
        a = self.type_(case_(self.value_low, ignoreCase))
        b = self.type_(case_(self.value_high, ignoreCase))
        c = case_(elem[self.column.name], ignoreCase)
        return a <= c <= b

    def __repr__(self):
        return "<%s >= %s && %s <= %s>" % (self.column, self.fmtval(self.value_low), self.column, self.fmtval(self.value_high))

    def sql(self):
        return between(self.column, self.value_low, self.value_high)

class NotRangeSearchRule(RangeSearchRule):
    """matches if a value is outside a specified range
    sqlite3: values are inclusive on the range specified
    """

    def check(self, elem, ignoreCase=True):
        a = self.type_(case_(self.value_low, ignoreCase))
        b = self.type_(case_(self.value_high, ignoreCase))
        c = case_(elem[self.column.name], ignoreCase)
        return c < a or c > b

    def __repr__(self):
        return "<`%s` not in range (%s,%s)>" % (self.column, self.fmtval(self.value_low), self.fmtval(self.value_high))

    def sql(self):
        return ~between(self.column, self.value_low, self.value_high)

class MetaSearchRule(SearchRule):
    """group one or more search rules"""

    def __init__(self, rules):
        super(MetaSearchRule, self).__init__()
        self.rules = rules

class AndSearchRule(MetaSearchRule):
    """MetaSearchRule which checks that all rules return true"""

    def check(self, elem, ignoreCase=True):
        for rule in self.rules:
            if not rule.check(elem, ignoreCase):
                break
        else:
            return True
        return False

    def __repr__(self):
        return "<" + ' && '.join(map(repr, self.rules)) + ">"

    def sql(self):
        return and_(*[rule.sql() for rule in self.rules])

    @staticmethod
    def join(*rules):
        """
        return a composite of a set of rules
        """
        rules = [rule for rule in rules if not isinstance(rule, BlankSearchRule)]
        if len(rules) == 0:
            return BlankSearchRule()
        if len(rules) == 1:
            return rules[0]
        return AndSearchRule(rules)

class OrSearchRule(MetaSearchRule):
    """MetaSearchRule which checks that at least one rule returns true"""

    def check(self, elem, ignoreCase=True):
        for rule in self.rules:
            if rule.check(elem, ignoreCase):
                return True
        return False

    def __repr__(self):
        return "[" + ' || '.join(map(repr, self.rules))  + "]"

    def sql(self):
        return or_(*[rule.sql() for rule in self.rules])

    @staticmethod
    def join(*rules):
        """
        return a composite of a set of rules
        """
        rules = [rule for rule in rules if not isinstance(rule, BlankSearchRule)]
        if len(rules) == 0:
            return BlankSearchRule()
        if len(rules) == 1:
            return rules[0]
        return OrSearchRule(rules)

class NotSearchRule(MetaSearchRule):
    """MetaSearchRule which checks that inverts result from rule"""

    def check(self, elem, ignoreCase=True):
        assert len(self.rules) == 1
        assert self.rules[0] is not BlankSearchRule
        if self.rules[0].check(elem, ignoreCase):
            return False
        return True

    def __repr__(self):
        assert len(self.rules) == 1
        assert self.rules[0] is not BlankSearchRule
        return "<!" + repr(self.rules[0]) + ">"

    def sql(self):
        return not_(self.rules[0].sql())

class MultiColumnSearchRule(SearchRule):
    """
    A combining rule for applying a rule to multiple columns

    this exists only to make debug statements easier to read
        when printing all_text rules
    """

    def __init__(self, rule, columns, value, colid="multi"):
        super(SearchRule, self).__init__()
        self.columns = columns
        self.value = value
        self.colid = colid

        meta = OrSearchRule
        self.operator = "="
        if rule in (InvertedPartialStringSearchRule, InvertedExactSearchRule):
            meta = AndSearchRule
            self.operator = "!="

        self.rule = meta([rule(col, value) for col in columns])

    def __repr__(self):
        return "< %s %s %s >" % (self.colid, self.operator, self.fmtval(self.value))

    def check(self, elem, ignoreCase=True):
        return self.rule.check(elem, ignoreCase)

    def sql(self):
        return self.rule.sql()

def naive_search(seq, rule, case_insensitive=True, orderby=None, \
    reverse=False, limit=None, offset=0, echo=False, columns=None):
    """ return elements from seq which match the given rule

    seq can be any iterable data structure containing table data
    for example a list-of-dict, or a sql database view.

    TODO: reverse is deprecated. it is handled by order by

    """
    # filter the sequence using the rule
    if columns is not None:
        out = [{k: v for k, v in elem.items() if k in columns}
            for elem in seq if rule.check(elem)]
    else:
        out = [elem for elem in seq if rule.check(elem)]

    if orderby is not None:
        if not isinstance(orderby, (tuple, list)):
            orderby = [orderby, ]

        for item in reversed(orderby):
            if isinstance(item, str):
                out = sorted(out, key=lambda s: s[item], reverse=False)
            else:
                key, mode = item
                out = sorted(out, key=lambda s: s[key], reverse=mode == "DESC")

    if offset:
        out = out[offset:]

    if limit:
        out = out[:limit]

    return out

class ParseError(Exception):
    pass

class TokenizeError(ParseError):
    pass

class RHSError(ParseError):
    def __init__(self, tok, value=""):
        msg = "Invalid Expression on RHS of `%s` at position %d" % (tok, tok.pos)
        if value:
            msg += " : %s" % value
        super(RHSError, self).__init__(msg)

class LHSError(ParseError):
    def __init__(self, tok, value=""):
        msg = "Invalid Expression on LHS of `%s` at position %d" % (tok, tok.pos)
        if value:
            msg += " : %s" % value
        super(LHSError, self).__init__(msg)

class FormatConversion(object):
    """
    FormatConversion handles conversion from string to another type.
    Using Object Composition simplifies computation out of SearchGrammar
    """

    def __init__(self, dtn=None):

        # locale date parsing, by default
        # YYYY/MM/DD is supported.
        # changing these values (indices into a 3-tuple)
        # will change the supported date format.
        self.DATE_LOCALE_FMT_Y = 0
        self.DATE_LOCALE_FMT_M = 1
        self.DATE_LOCALE_FMT_D = 2

        self.DATE_LOCALE_FMT_Y_2 = 0
        self.DATE_LOCALE_FMT_M_2 = 1

        self.datetime_now = dtn or datetime.now()

    def formatDateDelta(self, sValue):
        """
        parse strings of the form
            "12d" (12 days)
            "1y2m" (1 year 2 months)
            "1y2m3w4d" (1 year, 2 months, 3 weeks, 4 days)
            negative sign in front creates a date IN THE FUTURE
        """

        negate = False
        num = ""
        dy = dm = dd = 0
        for c in sValue:
            if c == "-":
                negate = not negate
            elif c == "y":
                dy = int(num)
                num = ""
            elif c == "m":
                dm = int(num)
                num = ""
            elif c == "w":
                dd += 7 * int(num)
                num = ""
            elif c == "d":
                dd += int(num)
                num = ""
            else:
                num += c
        if num:
            dd += int(num)  # make 'd' optional, and capture remainder

        if negate:
            # invert the direction of the date delta (past or future)
            dy *= -1
            dm *= -1
            dd *= -1

        dtn = self.datetime_now
        dt1 = self.computeDateDelta(dtn.year, dtn.month, dtn.day, dy, dm, dd)
        dt2 = dt1 + timedelta(1)
        return calendar.timegm(dt1.timetuple()), calendar.timegm(dt2.timetuple())

    def computeDateDelta(self, y, m, d, dy, dm, dd=0):
        """
            given (y,m,d) a valid date, add dy years, dm months, dd days.

            negative values will return a date in the future.
            positive values will return a date in the past.
        """
        y -= dy
        if dm != 0:
            # add/sub 1 to convert range 1..12 to 0..11 for math reasons
            t = (m - 1 - dm)
            y = y + t // 12
            m = t % 12 + 1

        # modulo fix the day by rolling up, feb 29 to march 1
        # or july 32 to aug 1st, if needed
        days = calendar.monthrange(y, m)[1]
        while d > days:
            d -= days
            m += 1
            if (m > 12):
                m -= 12
                y += 1
            days = calendar.monthrange(y, m)[1]

        new_date = datetime(y, m, d)
        if dd != 0:
            new_date = new_date - timedelta(dd)

        return new_date

    def adjustYear(self, y):
        """ convert an integer year into a 4-digit year
        guesses the century using the magnitude of small numbers
        """
        if 50 < y < 100:
            y += 1900
        if y < 50:
            y += 2000
        return y

    def formatDate(self, sValue):
        """
        accepts strings of the following form:
            [YY]YY/
            [YY]YY/MM
            [YY]YY/MM/
            [YY]YY/MM/DD
        a slash is used to differentiate from a bare integer, which
        is parsed elseware as a day-delta
        """
        x = sValue.split('/')
        x = [y for y in x if y]  # remove empty sections

        if len(x) == 1:
            # return a range covering the whole year
            y = int(x[0])
            y = self.adjustYear(y)
            if y < 1900:
                raise ParseError("Invalid Year `%s` at position %s." % (sValue, sValue.pos))
            dt1 = datetime(y, 1, 1)
            dt2 = self.computeDateDelta(y, 1, 1, -1, 0)
        elif len(x) == 2:
            # return a range covering the whole month
            y = int(x[self.DATE_LOCALE_FMT_Y_2])
            m = int(x[self.DATE_LOCALE_FMT_M_2])
            y = self.adjustYear(y)
            if y < 1900:
                raise ParseError("Invalid Year `%s` at position %s." % (sValue, sValue.pos))
            dt1 = datetime(y, m, 1)
            dt2 = self.computeDateDelta(y, m, 1, 0, -1)
        else:
            # return a range covering the given day
            y = int(x[self.DATE_LOCALE_FMT_Y])
            m = int(x[self.DATE_LOCALE_FMT_M])
            d = int(x[self.DATE_LOCALE_FMT_D])
            y = self.adjustYear(y)
            dt1 = datetime(y, m, d)
            dt2 = dt1 + timedelta(1)

        result = calendar.timegm(dt1.timetuple()), calendar.timegm(dt2.timetuple())
        return result

    def parseDuration(self, sValue):
        # input as "123" or "3:21"
        # convert hours:minutes:seconds to seconds
        m = 1
        t = 0
        try:
            for x in reversed(sValue.split(":")):
                if x:
                    t += int(x) * m
                m *= 60
        except ValueError:
            raise ParseError("Duration `%s` at position %d not well formed." % (sValue, sValue.pos))
        return t

    def parseYear(self, sValue):
        """ parse a string as a year

            90 => 1990
            15 => 2015
        """
        y = 0
        try:
            y = self.adjustYear(int(sValue))
        except ValueError:
            raise ParseError("Year `%s` at position %d not well formed." % (sValue, sValue.pos))
        return y

    def parseNLPDate(self, value):

        dt = NLPDateRange(self.datetime_now).parse(value)
        if dt:
            cf = calendar.timegm(dt[0].utctimetuple())
            if cf < 0:
                cf = 0
            rf = calendar.timegm(dt[1].utctimetuple())
            return cf, rf
        return None

class Grammar(object):
    """SearchGrammar is a generic class for building a db search engine

        This defines a query syntax for querying records by text, date, or time
        fields.

        new-style queries use boolean logic and a `column = value` syntax
            for example, "artist=Aldious" can turn into a sql query for
            searching the artist column for the string Aldious

            These types of queries can be grouped using parenthesis and
            operators && and || can be used to group them in powerful ways

        old-style queries are used for user friendly text searching.
            and text that does not fit into the rigid new-style framework
            is interpretted as an old style query.

            Just typing a string, e.g. "Aldious" will search ALL text fields
            for the given string. multiple strings can be typed in a row,
            separated by white space and will automatically be ORed together.
            so called 'Implicit Or', or you can use an explicit && .
            if a word begins with the sigil, it will be used to denote a
            column to search for, which is applied to each word after
            the sigil word. e.g. ".artist Aldious" is the same as the new-style
            "artist=Aldious". and "Blind Melon" is the same as the new-style
            "Blind || Melon"

            old style supports negate and modifiers, for example
                ".date < 5 > 3" is equivalent to "date < 5 && date > 3"
                ".date ! < 5" is equivalent to "date >= 6"

        Text Searches

            todo, use quotes, etc

        Date Searches
            todo date modifiers, NLP, etc

        Time Searches
            todo, in seconds, minutes or hours, x:y:z, etc

    """

    META_LIMIT  = "limit"   # sql limit
    META_OFFSET = "offset"  # sql offset
    META_DEBUG  = "debug"   # write output to stdout

    class TokenState(object):
        """ state variables for tokenizer """

        def __init__(self):
            self.tokens = []
            self.stack = [self.tokens]

            self.start = 0
            self.tok = ""

            self.quoted = False
            self.join_special = False  # join 'special' characters

        def append(self, idx, new_start, force=False):
            """ append a token to the top of the stack
                clear all special states
            """
            if self.tok or force:
                kind = "text"
                if self.join_special:
                    kind = "special"

                self.stack[-1].append(StrPos(self.tok, self.start, idx, kind))

            self.join_special = False
            self.quoted = False

            self.tok = ""
            self.start = new_start

        def push(self):
            new_level = []
            self.stack[-1].append(new_level)
            self.stack.append(new_level)

        def pop(self):
            self.stack.pop()

        def check(self):
            if len(self.stack) == 0:
                raise TokenizeError("Empty stack (check parenthesis)")
            if len(self.stack) > 1:
                raise TokenizeError("Unterminated Parenthesis")
            if self.quoted:
                raise TokenizeError("Unterminated Double Quote")

    def __init__(self, dtn=None):
        super(Grammar, self).__init__()

        # set these to names of columns of specific data types
        # type support is currently limited. it boils down to "string"
        # and "not string". add text columns to text_fields. a column
        # not found in a field listed below is assumed to be an integer
        # there is no support for float at the momeny. (would be easy to add)
        self.text_fields = set()
        self.date_fields = set()  # column represents a date in seconds since jan 1st 1970
        self.time_fields = set()  # column represents a duration, in seconds
        self.year_fields = set()  # integer that represents a year
        self.number_fields = set()

        self.compile_operators()

        self.autoset_datetime = True
        self.fc = FormatConversion(dtn)

    # public

    def ruleFromString(self, string):
        """ return a rule AST from a given input string """
        if self.autoset_datetime:
            self.fc.datetime_now = datetime.now()

        # reset meta options
        self.meta_options = dict()

        if string is None or not string.strip():
            return BlankSearchRule()
        tokens = self.tokenizeString(string)
        rule = self.parseTokens(tokens)
        if self.getMetaValue(Grammar.META_DEBUG) == 1:
            sys.stdout.write("%r\n" % (rule))
        elif self.getMetaValue(Grammar.META_DEBUG) == 2:
            sys.stdout.write("%s\n" % (rule.sqlstr()))
        return rule

    def translateColumn(self, colid):
        """ convert a column name, as input by the user to the internal name

            overload this function to provide shortcuts for different columns

            raise ParseError if colid is invalid
        """
        if colid not in self.text_fields and \
           colid not in self.date_fields and \
           colid not in self.time_fields and \
           colid not in self.year_fields and \
           colid not in self.number_fields and \
           colid != self.all_text:
            raise ParseError("Invalid column name `%s` at position %d" % (colid, colid.pos))
        return colid

    def getColumnType(self, key):
        return key

    def getMetaValue(self, colid, default=None):
        """ returns parsed value of a meta option, or default """
        return self.meta_options.get(colid, default)

    # private

    def tokenizeString(self, input):
        """
        split a string into tokens
        Supports nesting of parenthesis and quoted regions

        e.g.
            "x y z" becomes three tokens ["x", "y", "z"]
            "x && (y || z)" becomes ["x", "&&", ["y", "||", "Z"]]

        """
        idx = 0
        state = Grammar.TokenState()

        while idx < len(input) and len(state.stack) > 0:
            c = input[idx]

            if c == self.tok_escape:
                # skip the next character, by erasing the
                # current character from the input
                # TODO: to allow escape characters in strings
                # first check that we are quoted here
                # then look at the next character to decide
                # mode (e.g. \\ -> \, \a -> bell \x00 -> 0x00, etc)
                idx += 1
                if idx >= len(input):
                    raise TokenizeError("Escape sequence expected character at position %d" % idx)
                state.tok += input[idx]

            elif not state.quoted:
                if c == self.tok_quote:
                    state.append(idx, idx + 1)
                    state.quoted = True
                elif c == self.tok_nest_begin:
                    state.append(idx, idx + 1)
                    state.push()
                elif c == self.tok_nest_end:
                    state.append(idx, idx + 1)
                    state.pop()
                elif c in self.tok_whitespace:
                    state.append(idx, idx + 1)
                else:
                    s = c in self.tok_special
                    if s != state.join_special:
                        state.append(idx, idx)
                    state.join_special = s
                    state.tok += c
            else:  # is quoted
                if c == self.tok_quote:
                    state.append(idx, idx + 1, True)
                else:
                    state.tok += c
            idx += 1

        state.check()  # check the state machine for errors
        state.append(idx, idx)  # collect anything left over

        return state.tokens

    def parseTokens(self, tokens, top=True):
        """transforms the input tokens into an AST of SearchRules.
        """
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            hasl = i > 0
            hasr = i < len(tokens) - 1

            if isinstance(tok, list):
                # recursively process nested levels
                tokens[i] = self.parseTokens(tok, top=False)
                # completely remove useless rules
                if isinstance(tokens[i], BlankSearchRule):
                    tokens.pop(i)
                    continue
            elif tok.startswith(self.sigil):
                # old style query, replace consecutive words
                # with rules built in the old-way
                # intentionally ignores negate for legacy reasons
                s = i
                while i < len(tokens) and \
                        not isinstance(tokens[i], list) and \
                        tokens[i] not in self.operators_flow:
                    i += 1
                toks = tokens[:s]
                toks.append(self.parseTokensOldStyle(tokens[s:i]))
                toks += tokens[i:]
                tokens = toks
                i = s + 1
                continue
            elif tok in self.operators:
                if not hasr:
                    raise RHSError(tok, "expected value [V01]")
                r = tokens.pop(i + 1)
                if not isinstance(r, str):
                    raise RHSError(tok, "expected string [S01]")
                if r.kind == "special":
                    raise RHSError(tok, "unexpected operator `%s` [U01]" % r)
                # left side is optional, defaults to all text
                if not hasl or \
                        (not isinstance(tokens[i - 1], str) or tokens[i - 1] in self.operators_flow):
                    # no left side, or left side has been processed and is not a column label
                    tokens[i] = self.buildRule(self.all_text, self.operators[tok], r)
                else:
                    # left side token exists
                    i -= 1
                    l = tokens.pop(i)
                    if l in self.meta_columns:
                        # and remove the column name
                        tokens.pop(i)  # remove the operator
                        self.addMeta(l, tok, r, top)
                        continue
                    else:
                        # overwrite the operator with a rule
                        tokens[i] = self.buildRule(l, self.operators[tok], r)
            elif tok in self.special:
                if not hasr:
                    raise RHSError(tok, "expected value [V02]")
                if not hasl:
                    raise LHSError(tok, "expected value [V03]")
                r = tokens.pop(i + 1)
                if not isinstance(r, str):
                    raise RHSError(tok, "expected string [S02]")
                if r.kind == "special":
                    raise RHSError(tok, "unexpected operator `%s` [U02]" % r)
                i -= 1
                l = tokens.pop(i)
                if not isinstance(l, str):
                    raise LHSError(tok, "expected string [S03]")
                if l in self.meta_columns:
                    # and remove the column name
                    tokens.pop(i)  # remove token
                    self.parserMeta(l, tok, r, top)
                    continue
                tokens[i] = self.buildRule(l, self.special[tok], r)

            elif tok not in self.operators_flow and tok.kind == "special":
                # check for malformed operators
                raise ParseError("Unknown operator `%s` at position %d" % (tok, tok.pos))
            i += 1

        # collect any old style tokens, which did not use a sigil
        self.parseTokensOldStyle(tokens)

        # conditionally process logical operators if defined by the grammar
        optok = self.operators_flow_invert.get(NotSearchRule, None)
        if optok is not None:
            self.processLogicalNot(tokens, optok)

        optok = self.operators_flow_invert.get(AndSearchRule, None)
        if optok is not None:
            self.processLogical(tokens, optok)

        optok = self.operators_flow_invert.get(OrSearchRule, None)
        if optok is not None:
            self.processLogical(tokens, optok)

        if len(tokens) == 0:
            return BlankSearchRule()

        elif len(tokens) == 1:
            if isinstance(tokens[0], str):
                # there should be no strings at this point
                raise ParseError("unexpected error")
            return tokens[0]

        return self.operators_flow_join(tokens)

    def processLogical(self, tokens, operator):
        """ left to right """
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if isinstance(tok, StrPos) and tok == operator:
                hasl = i > 0
                hasr = i < len(tokens) - 1
                if not hasr:
                    raise RHSError(tok, "expected value [V05]")
                if not hasl:
                    raise LHSError(tok, "expected value [V06]")
                r = tokens.pop(i + 1)
                if isinstance(r, StrPos) and r in self.operators_flow:
                    raise RHSError(tok, "unexpected operator `%s` [U03]" % r)
                i -= 1
                l = tokens.pop(i)
                tokens[i] = self.operators_flow[tok]([l, r])
            i += 1

    def processLogicalNot(self, tokens, operator):
        """ right to left """
        i = len(tokens) - 1
        while i >= 0:
            tok = tokens[i]
            if isinstance(tok, str) and tok == operator:
                hasl = i > 0
                hasr = i < len(tokens) - 1
                if not hasr:
                    raise RHSError(tok, "expected value [V04]")
                r = tokens.pop(i + 1)
                if isinstance(r, str) and r in self.operators_flow:
                    raise RHSError(tok, "unexpected operator `%s` [U03]" % r)
                tokens[i] = NotSearchRule([r, ])
            i -= 1

    def parseTokensOldStyle(self, tokens):

        current_col = self.all_text
        current_opr = PartialStringSearchRule

        i = 0
        while i < len(tokens):
            tok = tokens[i]

            if isinstance(tokens[i], str):
                if tok.startswith(self.sigil):
                    current_col = StrPos(tok[1:], tok.pos + 1, tok.end, tok.kind)
                    tokens.pop(i)
                    continue
                elif tok not in self.operators_flow:
                    tokens[i] = self.buildRule(current_col, current_opr, tok)
            i += 1

        # return the single rule of a meta rule of all rules
        if len(tokens) == 1:
            return tokens[0]
        return self.operators_flow_join(tokens)

    def addMeta(self, colid, tok, value, top):
        """ meta options control sql parameters of the query
        They are independent of any database.
        """
        if not top:
            raise ParseError("Option `%s` at position %d can only be provided at the top level." % (colid, colid.pos))

        if colid in self.meta_options:
            raise ParseError("Option `%s` at position %d can not be provided twice" % (colid, colid.pos))

        if tok not in self.operators:
            raise ParseError("Operator `%s` at position %d not valid in this context" % (tok, tok.pos))

        rule = self.operators[tok]

        if colid == Grammar.META_DEBUG:
            self.meta_options[colid] = int(value)
        elif colid in (Grammar.META_LIMIT, Grammar.META_OFFSET):

            if rule in (PartialStringSearchRule, ExactSearchRule):
                self.meta_options[colid] = int(value)
            else:
                raise ParseError("Illegal operation `%s` at position %d for option `%s`" % (tok, tok.pos, colid))

    # protected

    def compile_operators(self):
        raise NotImplementedError()

    def buildRule(self, colid, rule, value):
        raise NotImplementedError()

class SearchGrammar(Grammar):

    def __init__(self, dtn=None):
        super(SearchGrammar, self).__init__(dtn)

    def compile_operators(self):

        self.all_text = 'text'
        # sigil is used to define the oldstyle syntax marker
        # it should not appear in tok_special
        self.sigil = '.'

        # tokens control how the grammar is parsed.
        self.tok_whitespace = " \t"  # token separators
        # all meaningful non-text chars
        self.tok_operators = '~!=<>'
        self.tok_flow = "|&"
        self.tok_special = self.tok_operators + self.tok_flow
        self.tok_negate = "!"
        self.tok_nest_begin = '('
        self.tok_nest_end = ')'
        self.tok_quote = "\""
        self.tok_escape = "\\"

        # does not require left token
        self.operators = {
            "=": PartialStringSearchRule,
            "~": PartialStringSearchRule,
            "==": ExactSearchRule,
            "=~": RegExpSearchRule,
            "!=": InvertedPartialStringSearchRule,
            "!==": InvertedExactSearchRule,
        }

        self.operators_invert = {
            InvertedPartialStringSearchRule: PartialStringSearchRule,
            InvertedExactSearchRule: ExactSearchRule,
            PartialStringSearchRule: InvertedPartialStringSearchRule,
            ExactSearchRule: InvertedExactSearchRule,
        }

        # require left/right token
        self.special = {
            "<": LessThanSearchRule,
            ">": GreaterThanSearchRule,
            "<=": LessThanEqualSearchRule,
            ">=": GreaterThanEqualSearchRule,
        }

        self.special_invert = {
            GreaterThanSearchRule: LessThanSearchRule,
            LessThanSearchRule: GreaterThanSearchRule,
            GreaterThanEqualSearchRule: LessThanEqualSearchRule,
            LessThanEqualSearchRule: GreaterThanEqualSearchRule,
        }

        # meta optins can be used to control the query results
        # by default, limit could be used to limit the number of results

        self.meta_columns = set([Grammar.META_LIMIT, Grammar.META_OFFSET, Grammar.META_DEBUG])
        self.meta_options = dict()

        self.old_style_operators = self.operators.copy()
        self.old_style_operators.update(self.special)

        self.old_style_operators_invert = self.operators_invert.copy()
        self.old_style_operators_invert.update(self.special_invert)

        self.operators_flow = {
            "&&": AndSearchRule,
            "||": OrSearchRule,
            "!": NotSearchRule,
        }

        self.operators_flow_invert = {v: k for k, v in self.operators_flow.items()}

        self.operators_flow_join = AndSearchRule

    def buildRule(self, colid, rule, value):
        """
        this must be expanded to support new data formats.
        """
        col = self.translateColumn(colid)

        if col == self.all_text:
            return self.allTextRule(rule, value)
        elif col in self.text_fields:
            return rule(self.getColumnType(col), value)
        elif col in self.date_fields:
            return self.buildDateRule(self.getColumnType(col), rule, value)
        # numeric field
        # partial rules don't make sense, convert to exact rules
        if col in self.time_fields:
            value = self.fc.parseDuration(value)

        if col in self.year_fields:
            value = self.fc.parseYear(value)

        type_ = str
        if col not in self.text_fields:
            type_ = int
        if rule is PartialStringSearchRule:
            return ExactSearchRule(self.getColumnType(col), value, type_=type_)
        if rule is InvertedPartialStringSearchRule:
            return InvertedExactSearchRule(self.getColumnType(col), value, type_=type_)
        return rule(self.getColumnType(col), value, type_=type_)

    def buildDateRule(self, col, rule, value):
        """
        There are two date fields, 'last_played' and 'date_added'

        queries can be run in two modes.

        providing an integer (e.g. date < N) performs a relative search
        from the current date, in this examples songs played since N days ago.

        providing a date string will run an exact search. (e.g. date < 15/3/12)
        the string is parsed y/m/d but otherwise behaves exactly the same way.

        < : closer to present day, including the date given
        > : farther into the past, excluding the given date
        = : exactly that day, from 00:00:00 to 23:59:59
        """
        c = value.count('/')

        invert = False
        try:
            if c > 0:
                # if there are any slashes assume the user wants to
                # parse the string as some form of YYYY/MM/DD
                epochtime, epochtime2 = self.fc.formatDate(value)
            elif c > 2:
                # the user gave two many separators for the date to make sense
                # TODO: create a special format for YY/MM/DD since that it can
                # be modified for other orders
                raise ParseError("Invalid Date format `%s` at position %d. Expected YY/MM/DD." % (value, value.pos))
            else:
                # parse the bare integer as a day-delta
                epochtime, epochtime2 = self.fc.formatDateDelta(value)
                invert = True
        except ValueError as e:
            # something went wrong trying to parse the date, try parsing
            # it as a natural string instead
            result = self.fc.parseNLPDate(value)

            if result is None:
                # failed to convert istr -> int
                raise ParseError("Expected Integer or Date, found `%s` at position %d" % (value, value.pos))

            epochtime, epochtime2 = result

        # flip the context of '<' and '>'
        # for dates, '<' means closer to present day
        # date < 5 is anything in the last 5 days
        # only invert when giving a relative date range
        # inverted query when giving an absolute date is confusing
        if invert and rule in self.special_invert:
            rule = self.special_invert[rule]

        # token '=' is partial string matching, in the context of dates
        # it will return any song played exactly n days ago
        # a value of '1' is yesterday
        if rule is PartialStringSearchRule:
            return RangeSearchRule(col, IntDate(epochtime), IntDate(epochtime2), type_=int)

        # inverted range matching
        if rule is InvertedPartialStringSearchRule:
            return NotRangeSearchRule(col, IntDate(epochtime), IntDate(epochtime2), type_=int)

        # todo: this needs further testing due to recent change
        # if invert is true, use less than equal
        # if invert is false, use greater than equal (i believe this is needed)
        if invert and rule is LessThanEqualSearchRule:
            return rule(col, IntDate(epochtime2), type_=int)

        return rule(col, IntDate(epochtime), type_=int)

    def allTextRule(self, rule, string):
        """
        returns a rule that will return true if
        any text field matches the given string
        or if no text field contains the string
        """
        cols = [self.getColumnType(f) for f in self.text_fields]
        return MultiColumnSearchRule(rule, cols, string, colid=self.all_text)

