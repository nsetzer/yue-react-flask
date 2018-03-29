#! python34 $this
import sys,os
import traceback

# TODO: this was written for python2, probably doesnt work with 3.

class Logger(object):
    instance = None
    BUFFER = -1 # if used as stdout= make a buffering logger
    """
    usage:
        from yue.core.logger import Logger
        Logger(trace=True).register()

    optional argument stdout must implement a write() method.
    use a custom stdout arguments to write to a file or
    to a Qt dialog for example.
    """
    def __init__(self,writer=None,trace=False,echo=False):
        """stdout must be an object implementing a write() method"""
        super(Logger, self).__init__()

        if writer == Logger.BUFFER:
            self.writer = Buffer()
        else:
            self.writer = writer or sys.__stdout__
        self.trace = trace
        self._echo = echo
        self.echo = echo and self.writer is not sys.__stdout__

        self.buffer = BinaryWriter( self )

    @staticmethod
    def register(inst=None):
        if inst is None:
            inst = Logger()
        Logger.instance = inst
        sys.stdout = inst
        sys.stderr = ErrorLogger(inst)

    def setWriter(self,writer):
        self.writer = writer
        self.echo = self._echo and self.writer is not sys.__stdout__

    def enableTraceback(self,trace):
        self.trace = trace

    def history(self):
        if isinstance(self.writer,Buffer):
            return self.writer.buffer
        return []
    #---------------------------------
    def error(self,string):
        # shortcut to the stderr writer
        sys.stderr.write(string)

    #----------------------------------
    # functions that emulate a file() like object
    def write(self,string):

        if self.trace and len(string.strip()) > 0:
            string = self.getTrace()+string

        try:
            self.writer.write(string)

            if self.echo and sys.__stdout__ is not None :
                sys.__stdout__.write(string)
        except UnicodeEncodeError as e:
            sys.__stderr__.write(self.getTrace()+"\n")
        except UnicodeDecodeError as e:
            sys.__stderr__.write(self.getTrace()+"\n")
        except AttributeError as e:
            sys.__stderr__.write(self.getTrace()+"\n")
        except Exception as e:
            sys.__stderr__.write(self.getTrace()+"\n")

    def getTrace(self):
        tr = traceback.extract_stack()
        for file_name,line_number,function,line in tr[::-1]:
            if file_name != __file__:
                _,name = os.path.split(file_name)
                return "%s:%d "%(name,line_number)
        return "<no trace>"

    def writelines(self,seq):
        for s in seq:
            self.write(s)

    def flush(self):
        pass

    def close(self):
        pass

    def isatty(self):
        return False

    def __call__(self,*args):
        self.writelines(args)

    def _instance():
        return Logger.instance

class BinaryWriter(object):

    def __init__(self, parent):
        super(BinaryWriter, self).__init__()
        self.parent = parent

    def write(self,b):
        # TODO: redirect to parent.writer
        sys.__stdout__.buffer.write( b )

class ErrorLogger(Logger):
    """docstring for ErrorLogger"""
    def __init__(self, parent):
        super(ErrorLogger, self).__init__()
        self.parent = parent

    def write(self,string):
        # TODO: this code as written isnt useful
        # what i want instead:
        # determine the file that is writing the current error stream
        # prior to writing the output, write the name of the file if
        # it is not the last file written to the stream.
        #if string.strip():
        #    if not self.parent.trace:
        #        trace = self.parent.getTrace()
        #        if 'traceback.py' not in trace:
        #            string = trace + string
        #            if string[-1] != "\n":
        #                string += "\n"
        self.parent.write(string)

class Buffer(object):
    """docstring for Buffer"""
    def __init__(self):
        super(Buffer, self).__init__()
        self.buffer = []

    def write(self,utf8str):
        self.buffer.append(utf8str)

if __name__ == '__main__':

    Logger().register()

    print("hello hello",end='-')
    print("Hello")
    print("Hello")
    sys.stdout.write("out\n")
    sys.stderr.write("error\n")
    print(u"\u0065\u4065123")
    #print("Hello","goodbye",sep='-')

    print(Logger.instance)