import re
from collections import namedtuple

class Format( object ):
    '''
    Class for reading fortran formatted data using a fortran format specification
    to define fixed length fields.  
    '''

    def __init__( self, format, names=None, trim=False ):
        '''
        Create a parser for specified format.

        format - the fortran format specification
        names  - a list of field names.  If supplied then a named tuple is returned
                 using these names.  If omitted then a tuple is returned
        trim - if True then string fields are trimmed
        '''
        self.setFormat( format, names, trim )

    def setFormat( self, format, names=None, trim=False ):
        format=format.upper()
        self._fields = []
        self._format = format
        # Expand repeat groups
        while re.search(r'\d\([^\)]+\)',format):
            format = re.sub(r'(\d+)\(([^\)]+)\)',
                            lambda m: ','.join(int(m.group(1))*[m.group(2)]),
                            format)
        format = re.sub(r'^\((.*)\)$',r'\1',format.strip())
        # Check that it matches a valid format
        if not re.match( r'''
                        (\d*X |
                         \d*[F]\d+\.\d+ |
                         \d*[IHA]\d+ 
                        )
                        (\,|$)+
                        ''',
                        format,
                        re.X ):
            raise ValueError('Invalid format specification: '+self._format)
        # Extract the fields
        fields = []
        ffloat = lambda x: float(x.replace('D','E'))
        fstr = (lambda x: str(x).strip()) if trim else str
        for m in re.findall('(\d*)(X|[FIAH](\d*))',format):
            fields.append((
                int(m[0] or 1),
                int(m[2] or 1),
                int if m[1][0]=='I' else
                ffloat if m[1][0]=='F' else
                fstr if m[1][0] in 'AH' else
                None
            ))
        self._fields = fields
        self._length = sum( (f[0]*f[1] for f in fields) )
        self._fieldcount = sum( f[0] for f in fields if f[2])
        if names:
            fieldnames=names.split()
            if len(fieldnames) != self._fieldcount:
                raise ValueError('Number of field names in "'+names+'" doesn\'t match format "'+self._format+'"')
            rectype=namedtuple('record',fieldnames)
            self._rectype=lambda x: rectype(*x)
        else:
            self._rectype=tuple

    def read( self, data ):
        '''
        Parse a string using the format
        '''
        values = []
        pos = 0
        if len(data) < self._length:
            data = data + ' '*(self._length)
        for count, width, ftype in self._fields:
            for c in range(count):
                s = data[pos:pos+width]
                pos += width
                if ftype:
                    values.append(ftype(s))
        return self._rectype(values)

    def readiter( self, stream, skipErrors=False, skipBlanks=False ):
        '''
        Iterator returning parsed data from a file stream

        stream - the stream to read
        skipErrors - if True then records not matching the format are skipped
        skipBlanks - if True then blank records are skipped
        '''
        for l in stream:
            if skipBlanks and l.strip() == '':
                continue
            try:
                yield self.read(l)
            except:
                if not skipErrors:
                    raise

    def readfile( self, filename, skipErrors=False, skipLines=0, skipBlanks=False ):
        '''
        Iterator returning parsed data from a file

        filename - the name of the file to read
        skipLine - the number of lines at the beginning of hte file to skip over
        skipErrors - if True then records not matching the format are skipped
        skipBlanks - if True then blank records are skipped
        '''
        f=None
        try:
            if filename.endswith('.gz'):
                import gzip
                f=gzip.open(filename,'rb')
            else:
                f=open(filename)
            for i in range(skipLines):
                f.readline()
            for r in self.readiter(f,skipErrors=skipErrors,skipBlanks=skipBlanks):
                yield r
        finally:
            if f is not None:
                f.close()

