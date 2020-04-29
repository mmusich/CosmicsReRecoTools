# CosmicsReRecoTools

```
cmsrel CMSSW_11_1_0_pre6
cd CMSSW_11_1_0_pre6/src
cmsenv
git cms-init # if you want to merge some CMSSW changes
git cms-merge-topic mmusich:rehaulCDC
git clone git@github.com:mmusich/CosmicsReRecoTools.git --branch CDCReReco
cd CosmicsReRecoTools
python submitAllTemplatedJobs.py -i ReRecoForCDC.ini -j Nominal -s
```