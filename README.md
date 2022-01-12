# BstarToTW_CMSDAS2022_BackgroundEstimation
Background estimation for the 2022 CMSDAS b*->tW exercise, using the updated version of 2DAlphabet

## Getting started (in bash shell)

### Setup CMSSW environment:
Assuming you've already created the `~/nobackup/CMSDAS2022/b2g_exercise/` directory:
```
ssh -XY USERNAME@cmslpc-sl7.fnal.gov
export SCRAM_ARCH=slc7_amd64_gcc700
cd nobackup/CMSDAS2022/b2g_exercise/
cmsrel CMSSW_10_6_14
cd CMSSW_10_6_14/src
cmsenv
```

### While still in the `src` directory:
```
git clone https://github.com/lcorcodilos/2DAlphabet.git
git clone https://github.com/lcorcodilos/HiggsAnalysis-CombinedLimit.git HiggsAnalysis/CombinedLimit/
curl -s https://raw.githubusercontent.com/lcorcodilos/CombineHarvester/master/CombineTools/scripts/sparse-checkout-ssh.sh | bash
scram b clean; scram b -j 4
cmsenv
python -m virtualenv twoD-env
source twoD-env/bin/activate
cd 2DAlphabet
git checkout refactor
python setup.py develop
```
Then, check that the installation worked with (in a python shell):
```
import ROOT
r = ROOT.RooParametricHist()
```

### Finally, clone this repo to the `src` directory as well:
```
git clone https://github.com/ammitra/BstarToTW_CMSDAS2022_BackgroundEstimation.git
```
OR fork the code onto your own personal space and set the upstream:
```
https://github.com/<USERNAME>/BstarToTW_CMSDAS2022_BackgroundEstimation.git
cd BstarToTW_CMSDAS2022_BackgroundEstimation
git remote add upstream https://github.com/ammitra/BstarToTW_CMSDAS2022_BackgroundEstimation.git
git remote -v
```
