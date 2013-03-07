import unittest
import contextlib

from pade.test.utils import tempdir
from pade.schema import Schema

from pade.metadb import *
from StringIO import StringIO

@contextlib.contextmanager
def temp_metadb():
    with tempdir() as d:
        mdb = MetaDB(d, 'test')
        mdb.redis.flushdb()
        yield mdb

class MetaDBTest(unittest.TestCase):

    def _next_obj_id(self):
        with temp_metadb() as mdb:
            a = mdb._next_obj_id('input_file')
            b = mdb._next_obj_id('input_file')
            self.assertGreater(b, a)

    def _input_files(self):
        with temp_metadb() as mdb:

            a = mdb.add_input_file("test.txt", "Some comments", StringIO("a\nb\nc\n"))
            b = mdb.add_input_file("foo.txt", "Other comments", StringIO("1\n2\n3\n"))

            # Make sure it returned the object appropriately
            self.assertEquals(a.name, "test.txt")
            self.assertEquals(a.comments, "Some comments")
            with open(a.path) as f:
                self.assertEquals("a\nb\nc\n", f.read())

            # Make sure we can list all input files
            input_files = mdb.all_input_files()
            self.assertEquals(len(input_files), 2)
            names = set(['test.txt', 'foo.txt'])
            self.assertEquals(names, set([x.name for x in input_files]))

    def test_schemas(self):
        with temp_metadb() as mdb:
            schema_a = Schema()
            schema_a.add_factor('treated', [False, True])
            schema_a.set_columns(['id', 'a', 'b'],
                                 ['feature_id', 'sample', 'sample'])
            schema_a.set_factor('a', 'treated', False)
            schema_a.set_factor('b', 'treated', True)

            schema_b = Schema()
            schema_b.add_factor('age', ['young', 'old'])
            schema_b.set_columns(['key', 'foo', 'bar'],
                                 ['feature_id', 'sample', 'sample'])
            schema_b.set_factor('foo', 'age', 'young')
            schema_b.set_factor('bar', 'age', 'old')

            a = mdb.add_schema("First one", "The first one", schema_a)
            b = mdb.add_schema("Second", "Other", schema_b)
            
            self.assertEquals(a.name, "First one")
            self.assertEquals(a.comments, "The first one")
            
            schemas = mdb.all_schemas()
            self.assertEquals(len(schemas), 2)

            colnames = set()
            for s in schemas:
                schema = s.load()
                colnames.update(schema.column_names)
            self.assertEquals(colnames, set(['id', 'a', 'b',
                                             'key', 'foo', 'bar']))

if __name__ == '__main__':
    unittest.main()
