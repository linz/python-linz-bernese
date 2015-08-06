import numpy as np
import pandas as pd
import Util
from LINZ.Geodetic.Ellipsoid import GRS80
from Fortran import Format
from collections import namedtuple

StationCoord=namedtuple('StationCoord','id code name xyz flag')

def read( filename, skipError=False ):
    '''
    Read a bernese coordinate file and returns a dictionary of StationData
    keyed on station code.
    '''
    coords={}
    crdfmt=Format('I3,2X,A16,3F15.4,4X,A1','id name X Y Z flag',True)
    try:
        for data in crdfmt.readfile(Util.expandpath(filename),skipLines=6,skipBlanks=True,skipErrors=True):
                coords[data.name]=StationCoord(data.id,data.name[:4],data.name,[data.X,data.Y,data.Z],data.flag)
    except:
        if not skipError:
            raise
    return coords

def compare( codes=None, codesCoordFile=None, **files ):
    '''
    Compare two or more bernese coordinate files, and return a pandas DataFrame of
    common codes. 

    File names or coord data are entered as key/value pairs where the key is used to identify
    the data in the Dataframe (ie coordinate columns are key_X, key_Y, key_Z)

    Can take a list of codes to include in the comparison as either a list [codes], 
    string [codes], or bernese coordinate file containing the codes [codesCoordFile]

    If just two files are compared then the differences are included in the data frame.
    '''
    coords={}
    usecodes=None
    nfiles=0
    for f in files:
        nfiles += 1
        crddata=files[f]
        if isinstance(crddata,basestring): 
            crddata=read(crddata)
        coords[f]=crddata
        fcodes=set(crddata)
        if usecodes is None:
            usecodes=fcodes
        else:
            usecodes=usecodes.intersection(fcodes)

    codelist=None
    if codes is not None:
        if isinstance(codes,basestring):
            codes=codes.split()
        usecodes=usecodes.intersection(set(codes))

    if codesCoordFile is not None:
        cfcodes=read(codesCoordFile)
        usecodes=usecodes.intersection(set(cfcodes))

    if nfiles == 0:
        raise RuntimeError("No files specified in CoordFile.Compare")
    if len(usecodes) == 0:
        raise RuntimeError("No common codes to compare in CoordFile.Compare")

    data=[]
    usecodes=sorted(usecodes)
    crdtypes=sorted(coords)
    calcdiff=len(crdtypes) == 2
    for code in sorted(usecodes):
        codedata=[code]
        cdata=[coords[t][code] for t in crdtypes]
        lon,lat,hgt=GRS80.geodetic(cdata[0].xyz)
        codedata.extend((lon,lat,hgt))
        codedata.extend((c.flag for c in cdata))
        for c in cdata:
            codedata.extend(c.xyz)
        if calcdiff:
            xyz0=np.array(cdata[0].xyz)
            xyz1=np.array(cdata[1].xyz)
            dxyz=xyz1-xyz0
            denu=GRS80.enu_axes(lon,lat).dot(dxyz)
            codedata.extend(dxyz)
            codedata.extend(denu)
        data.append(codedata)

    columns=['code','lon','lat','hgt']
    columns.extend((t+'_flg' for t in crdtypes))
    for  t in crdtypes:
        columns.extend((t+'_X',t+'_Y',t+'_Z'))
    if calcdiff:
        columns.extend(('diff_X','diff_Y','diff_Z','diff_E','diff_N','diff_U'))
    df=pd.DataFrame(data,columns=columns)
    df.set_index(df.code,inplace=True)
    return df


def compare_main():
    import argparse
    parser=argparse.ArgumentParser(description='Compare two bernese coordinate files')
    parser.add_argument('crd_file_1',help='Name of first CRD file (can enter as type=filename)')
    parser.add_argument('crd_file_2',help='Name of second CRD file (can enter as type=filename)')
    parser.add_argument('csv_file',nargs='?',help='Name of output CSV file of differences')
    args=parser.parse_args()

    cmpfiles={}
    for i,f in enumerate((args.crd_file_1,args.crd_file_2)):
        if '=' in f:
            k,v=f.split('=',1)
            cmpfiles[k]=v
        else:
            cmpfiles['crd'+str(i+1)]=f

    cmpdata=compare(**cmpfiles)
    if args.csv_file is not None:
        cmpdata.to_csv(args.csv_file,index=False)
    else:
        print cmpdata.loc[:,('diff_X','diff_Y','diff_Z','diff_E','diff_N','diff_U')].describe()

if __name__=='__main__':
    compare_main()

