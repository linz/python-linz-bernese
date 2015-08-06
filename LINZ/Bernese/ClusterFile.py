import Util
from Fortran import Format
from collections import namedtuple

StationCluster=namedtuple('StationCluster','code name clusters')

def read( f ):
    clusters={}
    clufmt=Format('A16,I5','name cluster',True)
    for data in clufmt.readfile(Util.expandpath(f),skipLines=5,skipBlanks=True):
        if data.name in clusters:
            clusters[data.name].clusters.append(data.cluster)
        else:
            clusters[data.name]=StationCluster(data.name[:4],data.name,[data.cluster])
    return clusters

