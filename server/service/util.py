
import os,sys
import subprocess

class FFmpegEncoder(object):
    def __init__(self,ffmpeg_path,logger=None,no_exec=False):
        super(FFmpegEncoder,self).__init__();
        self.ffmpeg = ffmpeg_path
        self.logger = logger
        if self.logger == None:
            self.logger = sys.stderr
        self.no_exec = no_exec

    def args_add_metadata(self,args,keyname,keyvalue):
        args.append(u"-metadata")

        args.append( "%s=%s"%(keyname,keyvalue) )

    def args_add_input(self,args,path):
        args.append("-i")
        args.append(path)

    def args_add_output(self,args,b,sr,c,vol,path):
        if b > 0:
            args.append("-ab")
            args.append(str(b)+'k')
        if c > 0:
            args.append(u"-ac")
            args.append(str(c))
        if sr > 0:
            args.append("-ar")
            args.append(str(sr))

        if vol != 1 and vol > .2:
            vol = max(0.2,vol)
            vol = min(2.0,vol)
            args.append("-vol")
            args.append("%d"%( 256 * vol))

        args.append("-y") # force writing to output file
        args.append(path)

    # old function, for old style sync
    def transcode(self,input,output,bitrate=0,samplerate=0,channels=-1,vol=1.0,metadata={}):

        try:
            args = [self.ffmpeg,]
            self.args_add_input(args,input)

            #self.args_add_metadata(args,"artist",metadata.get("artist","Unknown"))
            #self.args_add_metadata(args,"title",metadata.get("title","Unknown"))
            #self.args_add_metadata(args,"album",metadata.get("album","Unknown"))
            #args.append("-id3v2_version")
            #args.append("3")
            #args.append("-write_id3v1")
            #args.append("1")
            self.args_add_output(args,bitrate,samplerate,channels,vol,output)
        except Exception as e:
            print (str(e).encode('utf-8'))
            print (("error building args for %s"%input).encode('utf-8'))
            return;

        try:
            self.call(args)
        except Exception as e:
            print (str(e).encode('utf-8'))
            print (("error transcoding %s"%input).encode('utf-8'))

        return

    def call(self,args):
        argstr = u' '.join(args)
        if self.logger == sys.stderr:
            argstr = argstr.encode('utf-8')
        #self.logger.write( argstr )
        self.logger.write("transcode: "+" ".join(args) + "\n")
        # when run under windows (under gui)
        # std in/out/err must be given a PIPE/nul
        # otherwise: '[WinError 6] The handle is invalid'
        # shell must be true to prevent a cmd window from opening

        if not self.no_exec:
            subprocess.check_call(args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False)