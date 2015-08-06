import Util
from Fortran import Format
from collections import namedtuple

Station=namedtuple('Station','code name')

def read( f ):
    stns=[]
    stnfmt=Format('A16','name',True)
    for data in stnfmt.readfile(Util.expandpath(f),skipLines=5,skipBlanks=True):
        stns.append(Station(data.name[:4],data.name))
    return stns

