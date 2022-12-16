# BstarToTW_CMSDAS2022_BackgroundEstimation
Background estimation for the 2022 CMSDAS b*->tW exercise, using the updated version of 2DAlphabet

## Getting started (in bash shell)

First, ensure that you have [SSH keys tied to your github account](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent) and that they've been added to the ssh-agent:
```
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_xyz
```

### Setup CMSSW and 2DAlphabet environment:
Assuming you've already created the `~/nobackup/CMSDAS2023/` directory, first create the CMSSW environment:
```
ssh -XY USERNAME@cmslpc-sl7.fnal.gov
export SCRAM_ARCH=slc7_amd64_gcc700
cd nobackup/CMSDAS2023/
cmsrel CMSSW_10_6_14
cd CMSSW_10_6_14/src
cmsenv
```

Now set up 2DAlphabet:
```
cd ~/nobackup/CMSDAS2023/CMSSW_10_6_14/src/
git clone https://github.com/ammitra/2DAlphabet.git
git clone https://github.com/cms-analysis/HiggsAnalysis-CombinedLimit.git HiggsAnalysis/CombinedLimit
curl -s https://raw.githubusercontent.com/lcorcodilos/CombineHarvester/master/CombineTools/scripts/sparse-checkout-ssh.sh | bash
scram b clean; scram b -j 4
cmsenv
```

Now, create a virtual environment in which to install 2DAlphabet:
```
python -m virtualenv twoD-env
source twoD-env/bin/activate
cd 2DAlphabet
python setup.py develop
```

Then, check that the 2DAlphabet installation worked by opening a python shell:
```
python
```
then, inside the python shell:
```
import ROOT
r = ROOT.RooParametricHist()
```

### Finally, clone this repo to the `src` directory as well:
```
cd ~/nobackup/CMSDAS2023/CMSSW_10_6_14/src/
git clone https://github.com/ammitra/BstarToTW_CMSDAS2023_BackgroundEstimation.git
```
OR fork the code onto your own personal space and set the upstream:
```
https://github.com/<USERNAME>/BstarToTW_CMSDAS2023_BackgroundEstimation.git
cd BstarToTW_CMSDAS2023_BackgroundEstimation
git remote add upstream https://github.com/ammitra/BstarToTW_CMSDAS2023_BackgroundEstimation.git
git remote -v
```

## What to do after reconnecting to the LPC:
Go back to the directory where you installed 2DAlphabet and where the virtual environment resides:
```
ssh -XY USERNAME@cmslpc-sl7.fnal.gov
cd ~/nobackup/CMSDAS2023/CMSSW_10_6_14/src/
cmsenv
source twoD-env/bin/activate
```
Then you should be good to go!

## Background estimate
For this exercise we will use the [`2DAlphabet`](https://github.com/ammitra/2DAlphabet) github package. This package uses `.json` configuration files to specify the input histograms (to perform the fit) and the uncertainties. These uncertainties will be used inside of the `Higgs Combine` backend, the fitting package used widely within CMS. The 2DAlphabet package serves as a nice interface with Combine to allow the user to use the 2DAlphabet method without having to create their own custom version of combine. 

# Configuration file

The configuration file that you will be using is called `bstar.json`, located in this repository. Let's take a look at this file and see the various parts:

* `GLOBAL`
  - This section contains meta information regarding the location (`path`), filenames (`FILE`), and input histogram names (`HIST`) for all ROOT files used in the background estimation procedure.
  - Everything in this section will be used in a file-wide find-and-replace. So wherever you see the name of the sub-objects in this file, it will be expanded by the value assigned to it in this section. 
  - Additionally, the `SIGNAME` list should include the name(s) of all signals you wish to investigate, so that they are added to the workspace when you run the python script.
    - If you wanted to investigate limits for only three signals, for example, you'd just add their names as given in the ROOT files to this list. 
    - For this exercise, the default is `signalLH2400`, the 2.4 TeV signal sample. You'll want to change this as the exercise progresses

* `REGIONS`
  - This section contains the various regions we are interested in transferring between.
  - Each region contains a `PROCESSES` object, listing the signals and backgrounds to be included in the fit, as well as  `BINNING` object, which is defined elsewhere in the config file.
  - The name of each region in `REGIONS` is dependent on the input histogram name, as well as your choice of `HIST` name in the `GLOBAL` section above
    - For instance, in this file we declared `HIST = MtwvMt$region`, where `$region` will be expanded as the name given in `REGIONS`. 
    - We chose this name because the input histograms are titled `MtwvMtPass` and `MtwvMtFail` for the Pass and Fail regions, respectively. 

* `PROCESSES`
  - In this section we define all of the various process ROOT files that will be used to produce the fit. These include data, signals, and backgrounds.
  - Each process contains its own set of options:
    - `SYSTEMATICS`: a list of systematic uncertainties, whose properties are defined elsewhere in the config file
    - `SCALE`: how much to scale this process by in the fit
    - `COLOR`: color to plot in the fit (ROOT color schema)
    - `TYPE`: `DATA`, `BKG`, `SIGNAL`
    - `TITLE`: label in the plot legend (LaTeX compatible)
    - `ALIAS`: if the process has a different filename than standard, this will be what replaces `$process` in the `GLOBAL` section's `FILE` option, so that this process gets picked up properly
    - `LOC`: the location of the file, using the definitions laid out in `GLOBAL`

* `SYSTEMATICS`
  - This contains the names of all systematic uncertainties you want to apply to the various processes.
  - The `CODE` key describes the type of systematic that will be used in Combine.
  - The `VAL` key is how we assign the value of that uncertainty. For instance, a `VAL` of `1.018` in the `lumi` (luminosity) means that this systematic has a 1.8% uncertainty on the yield.

* `BINNING`
  - This section allows us to name and define custom binning schema. After naming the schema, one would define several variables for both `X` and `Y`:
    - `NAME`: allows us to denote what is being plotted on the given axis
    - `TITLE`: the axis label for the plot (LaTeX enabled)
    - `BINS`: a list of bins
    - `SIGSTART`, `SIGEND`: the bins defining a window `[SIGSTART, SIGEND]` around which to blind (if the blinded option is selected)

* `OPTIONS`
  - A list of boolean and other options to be considered when generating the fit
  - (explanation WIP)

# Running the ML fit
By default, the `bstar.py` python API should set up a workspace, perform the ML fit, and plot the distributions. 

```
python bstar.py
```

The output is stored in the `tWfits/` output directory by default.

# Systematics
Systematic uncertainties were described in the config file section above. Add the Top pT uncertainties to the appropriate processes in the config file, then re-run the fit after having copied the old Combine card somewhere safe. Compare the pre- and post-Top pT Combine cards using `diff`.

# Limit setting
WIP
