# CosmicsReRecoTools

```
cmsrel CMSSW_9_0_2
cd CMSSW_9_0_2/src
cmsenv
git cms-init # if you want to merge some CMSSW changes
git clone git@github.com:mmusich/CosmicsReRecoTools.git .
cd CosmicsReRecoTools
python submitAllTemplatedJobs.py -i testReReco_CRUZET2017_ML3andAPE.ini -j CRUZET_ReReco -s
```