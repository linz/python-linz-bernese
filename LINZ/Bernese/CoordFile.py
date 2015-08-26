#!/usr/bin/python
# Imports to support python 3 compatibility
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy as np
import numpy.linalg as la
import pandas as pd
import datetime
import re
import Util
from LINZ.Geodetic.Ellipsoid import GRS80
from Fortran import Format
from collections import namedtuple

class StationCoord( object ):

    def __init__(self, id, code, name, datum, crddate, xyz, vxyz, flag):
        self.id=id
        self.code=code
        self.name=name
        self.datum=datum
        self.crdate=crdate,
        self.xyz=xyz
        self.vxyz=vxyz
        self.flag

    def epochXyz( self, date=None ):
        if date is None or self.crddate is None or self.vxyz is None:
            return self.xyz
        ydiff=(date-self.crddate).days/365.242
        xyz=self.xyz
        vxyz=self.vxyz
        return [xyz[0]+vxyz[0]*ydiff,xyz[1]+vxyz[1]*ydiff,xyz[2]+vxyz[2]*ydiff]

def read( filename, velocityFilename=None, velocities=False, tryVelocities=False, skipError=False, useCode=False ):
    '''
    Read a bernese coordinate file and returns a dictionary of StationData
    keyed on station code.  If velocities is True then a matching .VEL file will be loaded.
    If tryVelocities is True then a velocity file will be tried, but the routine will not fail
    if it cannot be read.  If velocityFilename is specified then a velocity file will be loaded.  
    '''

    filename=Util.expandpath(filename)

    if tryVelocities or velocityFilename is not None:
        velocities=True

    dtmfmt=Format('22X,A18,7X,A20','datum epoch',True)
    crdfmt=Format('I3,2X,A16,3F15.4,4X,A1','id name X Y Z flag',True)

    veldata={}
    if velocities:
        try:
            if velocityFilename is None:
                velocityFilename=re.sub(r'(?:\.CRD((?:\.gz)?))?$',r'.VEL\1',filename)
            for data in crdfmt.readfile(velocityFilename,skipLines=6,skipBlanks=True,skipErrors=True):
                code=data.name[:4]
                key=code if useCode else data.name
                veldata[key]=[data.X,data.Y,data.Z]
        except:
            if not tryVelocities:
                raise

    coords={}
    
    if filename.endswith('.gz'):
        import gzip
        f=gzip.open(filename,'rb')
    else:
        f=open(filename)
    try:
        # Skip two header lines
        f.readline()
        f.readline()
        # Read datum line
        dtm=dtmfmt.read(f.readline())
        datum=dtm.datum
        match=re.match(r'(\d{4})\-(\d\d)-(\d\d)\s+(\d\d)\:(\d\d)\:(\d\d)',dtm.epoch)
        if match is None:
            raise RuntimeError('Invalid datum epoch '+dtm.epoch+' in '+filename)
        year,mon,day,hour,min,sec=(int(x) for x in match.groups())
        crddate=datetime.datetime(year,mon,day,hour,min,sec)
        try:
            for data in crdfmt.readiter(f,skipBlanks=True,skipErrors=True):
                code=data.name[:4]
                key=code if useCode else data.name
                xyz=[data.X,data.Y,data.Z]
                vxyz=veldata.get(key)
                coords[key]=StationCoord(data.id,code,data.name,datum,crddate,xyz,vxyz,data.flag)
        except:
            if not skipError:
                raise
    finally:
        f.close()
    return coords

def compare( codes=None, codesCoordFile=None, useCode=False, velocities=False, skipError=False, **files ):
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
            crddata=read(crddata,useCode=useCode,skipError=skipError,velocities=velocities)
        coords[f]=crddata
        fcodes=set(crddata)
        if usecodes is None:
            usecodes=fcodes
        else:
            usecodes=usecodes.intersection(fcodes)

    if nfiles == 0:
        raise RuntimeError("No files specified in CoordFile.Compare")
    if usecodes is None or len(usecodes) == 0:
        raise RuntimeError("No common codes to compare in CoordFile.Compare")

    codelist=None
    if codes is not None:
        if isinstance(codes,basestring):
            codes=codes.split()
        usecodes=usecodes.intersection(set(codes))

    if codesCoordFile is not None:
        cfcodes=read(codesCoordFile,useCode=useCode,skipError=skipError)
        usecodes=usecodes.intersection(set(cfcodes))

    if len(usecodes) == 0:
        raise RuntimeError("No common codes selected in CoordFile.Compare")

    data=[]
    usecodes=sorted(usecodes)
    crdtypes=sorted(coords)
    calcdiff=len(crdtypes) == 2
    for code in sorted(usecodes):
        codedata=[code]
        cdata=[coords[t][code] for t in crdtypes]
        lon,lat,hgt=GRS80.geodetic(cdata[0].xyz)
        if lon < 0:
            lon += 360.0
        codedata.extend((lon,lat,hgt))
        codedata.extend((c.flag for c in cdata))
        for c in cdata:
            codedata.extend(c.xyz)
            if velocities:
                codedata.extend(c.vxyz or [np.Nan,np.Nan,np.Nan])
        if calcdiff:
            xyz0=np.array(cdata[0].xyz)
            xyz1=np.array(cdata[1].xyz)
            dxyz=xyz1-xyz0
            denu=GRS80.enu_axes(lon,lat).dot(dxyz)
            codedata.extend(dxyz)
            codedata.extend(denu)
            codedata.append(la.norm(denu))
            if velocities:
                xyz0=np.array(cdata[0].vxyz or [np.NaN,np.NaN,np.NaN])
                xyz1=np.array(cdata[1].vxyz or [np.NaN,np.NaN,np.NaN])
                dxyz=xyz1-xyz0
                denu=GRS80.enu_axes(lon,lat).dot(dxyz)
                codedata.extend(dxyz)
                codedata.extend(denu)
                codedata.append(la.norm(denu))
        data.append(codedata)

    columns=['code','lon','lat','hgt']
    columns.extend((t+'_flg' for t in crdtypes))
    for  t in crdtypes:
        columns.extend((t+'_X',t+'_Y',t+'_Z'))
        if velocities:
            columns.extend((t+'_VX',t+'_VY',t+'_VZ'))
    if calcdiff:
        columns.extend(('diff_X','diff_Y','diff_Z','diff_E','diff_N','diff_U','offset'))
        if velocities:
            columns.extend(('diff_VX','diff_VY','diff_VZ','diff_VE','diff_VN','diff_VU','offsetV'))
    df=pd.DataFrame(data,columns=columns)
    df.set_index(df.code,inplace=True)
    return df


def compare_main():
    import argparse
    parser=argparse.ArgumentParser(description='Compare two bernese coordinate files')
    parser.add_argument('crd_file_1',help='Name of first CRD file (can enter as type=filename)')
    parser.add_argument('crd_file_2',help='Name of second CRD file (can enter as type=filename)')
    parser.add_argument('csv_file',nargs='?',help='Name of output CSV file of differences')
    parser.add_argument('-c','--use-code',action='store_true',help='Use station code rather than full name')
    parser.add_argument('-v','--use-velocities',action='store_true',help='Compare velocities as well as ')
    args=parser.parse_args()

    cmpfiles={}
    for i,f in enumerate((args.crd_file_1,args.crd_file_2)):
        if '=' in f:
            k,v=f.split('=',1)
            cmpfiles[k]=v
        else:
            cmpfiles['crd'+str(i+1)]=f

    cmpdata=compare(useCode=args.use_code,skipError=True,velocities=args.use_velocities,**cmpfiles)
    if args.csv_file is not None:
        cmpdata.to_csv(args.csv_file,index=False,float_format="%.6f")
    else:
        print(cmpdata.loc[:,('diff_X','diff_Y','diff_Z','diff_E','diff_N','diff_U')].describe());

if __name__=='__main__':
    compare_main()

