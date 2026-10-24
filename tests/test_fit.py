import io
import struct
import unittest
import zipfile
from fitdecode.utils import compute_crc
from companion.fit import parse_fit

# Build a tiny FIT file from defined bytes: 3 synthetic records, no real athlete.
def synthetic_fit():
    fields=[(253,4,0x86),(5,4,0x86),(6,2,0x84),(3,1,0x02),(4,1,0x02),(2,2,0x84)]
    definition=bytes([0x40,0,0])+struct.pack('<H',20)+bytes([len(fields)])+b''.join(bytes(f) for f in fields)
    data=definition
    for i in range(3):
        data+=bytes([0])+struct.pack('<IIHBBH',1_000_000+i*5,i*1500,3000,140+i,87,2600)
    header=struct.pack('<BBHI4s',14,0x20,2140,len(data),b'.FIT')
    header+=struct.pack('<H',compute_crc(header))
    content=header+data
    return content+struct.pack('<H',compute_crc(content))

class FitTests(unittest.TestCase):
    def test_decode_synthetic_fit_without_coordinates(self):
        d=parse_fit(synthetic_fit());self.assertEqual(len(d['records']),3)
        self.assertEqual(d['records'][1]['t'],5)
        self.assertEqual(d['records'][1]['distance'],15)
        self.assertEqual(d['records'][1]['speed'],3)
        self.assertEqual(d['records'][1]['cadence'],174)
        self.assertEqual(d['records'][1]['elevation'],20)
        self.assertNotIn('position_lat',d['records'][0])
    def test_zip_and_nonfit(self):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:z.writestr('synthetic.fit',synthetic_fit())
        self.assertEqual(len(parse_fit(stream.getvalue())['records']),3)
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:z.writestr('readme.txt','synthetic')
        self.assertEqual(parse_fit(stream.getvalue()),{'records':[],'laps':[]})
