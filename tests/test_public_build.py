import importlib.util
from pathlib import Path
import unittest
sp=importlib.util.spec_from_file_location('public_build',Path(__file__).parents[1]/'scripts/build.py')
b=importlib.util.module_from_spec(sp);sp.loader.exec_module(b)

class PublicBuildTests(unittest.TestCase):
    def test_unlicensed_database_cannot_enter_public_build(self):
        with self.assertRaises(AssertionError):b.validate_public_sources([{'source_id':'db','source_refs':['db']}],[{'id':'db','mode':'paid'}])
    def test_private_record_cannot_enter_public_build(self):
        with self.assertRaises(AssertionError):b.validate_public_sources([{'source_id':'public','source_refs':['public'],'visibility':'private'}],[{'id':'public','mode':'review'}])
    def test_public_reviewed_metadata_is_allowed(self):
        b.validate_public_sources([{'source_id':'public','source_refs':['public'],'visibility':'public'}],[{'id':'public','mode':'review'}])

if __name__=='__main__':unittest.main()
