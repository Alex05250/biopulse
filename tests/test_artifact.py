import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('wait_artifact',Path(__file__).parents[1]/'scripts/wait_artifact.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class ArtifactTests(unittest.TestCase):
    def test_waits_for_upload_to_be_visible_in_rest_api(self):
        results=iter([[],[{'id':7,'name':'github-pages','expired':False}]])
        pauses=[]
        self.assertEqual(mod.wait_for_artifact(lambda:next(results),pauses.append,attempts=2),7)
        self.assertEqual(pauses,[5])
    def test_never_deploys_an_absent_or_expired_artifact(self):
        with self.assertRaises(RuntimeError):mod.wait_for_artifact(lambda:[{'id':7,'name':'github-pages','expired':True}],lambda n:None,attempts=2)

if __name__=='__main__':unittest.main()
