"""Guard against artifact REST indexing lag observed after a successful upload."""
import json
import os
import time
import urllib.request

def wait_for_artifact(fetch,sleep=time.sleep,attempts=24):
    for attempt in range(attempts):
        artifacts=fetch()
        match=next((a for a in artifacts if a.get('name')=='github-pages' and not a.get('expired')),None)
        if match:return match['id']
        if attempt+1<attempts:sleep(5)
    raise RuntimeError('Uploaded Pages artifact is not visible in REST API; refusing to deploy missing artifact.')

def main():
    url='https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']+'/actions/runs/'+os.environ['GITHUB_RUN_ID']+'/artifacts'
    token=os.environ['GITHUB_TOKEN']
    def fetch():
        req=urllib.request.Request(url,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'BioPulse-build'})
        with urllib.request.urlopen(req,timeout=20) as res:return json.load(res).get('artifacts',[])
    id=wait_for_artifact(fetch)
    print('Pages artifact is visible and ready:',id)

if __name__=='__main__':main()
