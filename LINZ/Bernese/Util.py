import os
import re
import os.path
import sys

datadir=os.environ.get('P','')
userdir=os.environ.get('U','')
progdir=os.environ.get('X','')

def expandpath( path ):
    return path.replace('${P}',datadir).replace('${U}',userdir).replace('${X}',progdir)

def userfile( *names ):
    return os.path.join(userdir,*names) if userdir else ''

def campaignfile( *names ):
    campdir=''
    try:
        with open(userfile('PAN','MENU.INP')) as mi:
            for l in mi:
                m = re.match(r'\s*ACTIVE_CAMPAIGN\s+\d+\s+\"([^\"]*)\"\s*$',l)
                if m:
                    campdir=expandpath(m.group(1))
                    break
        if campdir:
            return os.path.join(campdir,*names)
    except:
        pass
    return ''





