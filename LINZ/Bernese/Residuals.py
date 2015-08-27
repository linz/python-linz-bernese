import sys
import re
import os
from collections import namedtuple
import numpy as np

from .Fortran import Format

Line=namedtuple('Line','num,code1,code2,st1,st2,nf,offset,period')
Line.code = lambda self: self.code1+':'+self.code2 if self.code2 else self.code1

class Residuals( object ):

    def __init__( self, filename ):
        self.filepath = filename
        self.filename = os.path.basename(filename)
        self.filetype=None
        self.fileformat=None
        self.srccprogram='PROGRAM'
        self.differencing=''
        self.obsdate='unspecified date'

        f = open(filename,"r")
        while True:
            l = f.readline()
            if re.match(r'^Num\s+Station\s+1',l):
                break
            m = re.match(r'^\s*(.*)\:\s+(.*?)\s*$',l)
            if m:
                item = m.group(1)
                value = m.group(2)
                if item=='Type of residual file':
                    self.filetype=value
                elif item=='Format of residual records':
                    self.fileformat=value
                elif item=='Program created the file':
                    self.srcprogram=value
                elif item=='Difference level of observations':
                    self.differencing=value
        f.readline()

        fmt = Format('(I3,2X,2A18,A10,3(X,I2),14X,4I2,I4,I5)')
        lines=[None]
        offsets = [0]
        while True:
            l=f.readline()
            if not l.strip():
                break
            num,st1,st2,obsdate,hour,min,sec,nf,f1,f2,f3,type,period=fmt.read(l)
            offset = (hour*3600+min*60+sec)/period
            offsets.append(offset)
            if num != len(lines):
                raise RuntimeError('Stations numbers not right in '+filename)
            code1,st1 = st1.split(' ',1)
            code2,st2 = st2.split(' ',1)
            lines.append(Line(num,code1,code2,st1.strip(),st2.strip(),nf,offset,period))


        offsets = np.array(offsets)
        self._skipTo(f,r'^Num\s+Epoch\s+')
        f.readline()
        data = np.loadtxt( f,
                          converters={5: lambda s:float(s.replace('D','E'))},
                          dtype={'names': ('line','epoch','satellite','residual'),
                                 'formats': ('i4','i4','i4','f4')},
                          usecols=(0,1,3,5)
                         )
        data['epoch'] += offsets[data['line']]
        data['epoch'] *= period
                                 
        self._data = data
        self.obsdate=obsdate
        self.line=self._data['line']
        self.epoch=self._data['epoch']
        self.satellite=self._data['satellite']
        self.residual=self._data['residual']
        self.satellites=np.unique(self.satellite)
        self._lines = lines
        self.lines=lines[1:]

    def _skipTo(self,f,regex):
        while True:
            l = f.readline()
            if not l:
                raise RuntimeError('Cannot interpret '+filename+' as Bernese residual file')
            if re.match(regex,l):
                break

    def plot(self,plot=None,lines=None,satellites=None,colourby=None,colourmap=None,legend=None,title=True):
        from matplotlib import pyplot

        if not plot:
            plot=pyplot

        if satellites:
            satellites = satellites.split() if type(satellites) == str else satellites
            satellites = [satellites] if type(satellites) != list else satellites
            satellites = [int(x) for x in satellites]
            satellites = [x for x in satellites if x in self.satellites]
        satellites = satellites or self.satellites
        linecodes=[]
        lines = lines.split() if type(lines) == str else lines
        for s in self.lines:
            if not lines:
                linecodes.append(s.num)
            else:
                if s.code() in lines:
                    linecodes.append(s.num)

        if not colourby:
            colourby = 'L' if len(linecodes) > 1 else 'S'

        if colourby.upper()[0] == 'L':
            colcodes = linecodes
            colfield = self.line
            labels = [self._lines[i].code() for i in linecodes]
            selcodes = satellites
            selfield = self.satellite

        else:
            colcodes = satellites
            colfield = self.satellite
            labels = ['Sat '+str(i) for i in satellites]
            selcodes = linecodes
            selfield = self.line
        mval = range(np.max(selfield)+1)
        mval = np.array([True if i in selcodes else False for i in range(np.max(selfield)+1)])
        mask = mval[selfield]
        
        if not colourmap:
            colourmap = pyplot.get_cmap('jet',len(colcodes))

        plots=[]
        for i, c in enumerate(colcodes):
            ma = np.logical_and(mask,colfield == c)
            clr = colourmap(i)
            plot.plot(self.epoch[ma],self.residual[ma],'+',color=clr,label=labels[i])

        if legend==None:
            legend = len(labels) > 1
        if legend:
            plot.legend(numpoints=1,
                       labelspacing=0.2,
                       borderpad=0.5,
                       prop={'size':7},
                       bbox_to_anchor=(1.01,1.0),
                       loc=2,
                       borderaxespad=0.0,
                      )
        if title:
            if type(title) == bool:
                title = self.srcprogram+' residuals: '+self.obsdate
            pyplot.title(title)

if __name__=='__main__':
    from matplotlib import pyplot as plt
    r = resfile(sys.argv[1])
    r.plot()
    plot.show()
    # cm = plt.get_cmap('spectral',max(r.satellite)+1)
    # plt.scatter(r.epoch,r.residual,c=r.satellite,marker='+',edgecolors=r.satellite,cmap=cm)
    # plt.show()




