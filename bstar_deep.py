from time import time
from TwoDAlphabet import plot
from TwoDAlphabet.twoDalphabet import MakeCard, TwoDAlphabet
from TwoDAlphabet.alphawrap import BinnedDistribution, ParametricFunction
from TwoDAlphabet.helpers import make_env_tarball
import ROOT
import os
import numpy as np

# for b*, the P/F regions are named MtwvMtPass and MtwvMtFail
# so, just need to find and replace Pass/Fail depending on which region we want
def _get_other_region_names(pass_reg_name):
    return pass_reg_name, pass_reg_name.replace('Pass','Fail')


def _select_signal(row, args):
    '''Used by the Ledger.select() method to create a subset of a Ledger.
    This function provides the logic to determine which entries/rows of the Ledger
    to keep for the subset. The first argument should always be the row to process.
    The arguments that follow will be the other arguments of Ledger.select().
    This function should ALWAYS return a bool that signals whether to keep (True)
    or drop (False) the row.

    To check if entries in the Ledger pass, we can access a given row's
    column value via attributes which are named after the columns (ex. row.process
    gets the "process" column). One can also access them as keys (ex. row["process"]).

    In this example, we want to select for signals that have a specific string
    in their name ("process"). Thus, the first element of `args` contains the string
    we want to find.

    We also want to pick a TF to use so the second element of `args` contains a
    string to specify the Background_args[1] process we want to use.

    Args:
        row (pandas.Series): The row to evaluate.
        args (list): Arguments to pass in for the evaluation.

    Returns:
        Bool: True if keeping the row, False if dropping.
    '''
    signame = args[0]
    if row.process_type == 'SIGNAL':
        if signame in row.process:
            return True
        else:
            return False
    else:
        return True

def make_workspace():
    '''
    Constructs the workspace for all signals listed in the "SIGNAME" list in the 
    "GLOBAL" object in the json config file. This allows for one complete workspace to be
    created in which all the desired signals exist for you to select from later. 
    '''

    # Create the twoD object which starts by reading the JSON config and input arguments to
    # grab input simulation and data histograms, rebin them if needed, and save them all
    # in one place (organized_hists.root). The modified JSON config (with find-replaces applied, etc)
    # is also saved as runConfig.json. This means, if you want to share your analysis with
    # someone, they can grab everything they need from this one spot - no need to have access to
    # the original files! (Note though that you'd have to change the config to point to organized_hists.root).
    twoD = TwoDAlphabet('tWfits_deep', 'bstar_deep.json', loadPrevious=False)

    # Create the data - BKGs histograms
    qcd_hists = twoD.InitQCDHists()

    '''
    Some explanation for the following few lines of code: 
      We're nominally running on input histograms whose Pass/Fail criteria is based on a top tag using
      tau32 + subjet b tag (as opposed to DeepAK8 or ParticleNet taggers).
      Tau32 (and, to an extent, the subjet b tag) are very correlated with m_top and slightly correlated 
      with m_tW such that the pass-fail ratio is not smooth at all. The correlations are complicated enough
      that the pass-fail ratio has very strange but distinct features. These features are modeled very well by 
      the MC, so the idea is to use the MC to describe the majority of this, and the larger leftover disagreements
      can be made up by a simple polynomial (line 118).
    '''

    # open the smooth QCD MC file and gather the pass/fail histograms
    smooth_MC_file = ROOT.TFile.Open('/eos/user/c/cmsdas/2023/long-ex-b2g/rootfiles/smooth_QCD_run2.root')
    smooth_MC_fail = smooth_MC_file.Get('out_fail_4_5_default_run2__mt_mtw')
    smooth_MC_pass = smooth_MC_file.Get('out_pass_4_5_default_run2__mt_mtw')
    # create the pass fail ratio by dividing the pass histogram by the fail via ROOT
    smooth_MC_rpf = smooth_MC_pass.Clone()
    smooth_MC_rpf.Divide(smooth_MC_fail)

    # There are only 'Pass' and 'Fail' in twoD.ledger.GetRegions(), 
    # since we only have a 'Pass' and a 'Fail' region in the input histos.
    # Therefore, this loop will only run once. 
    for p, f in [_get_other_region_names(r) for r in twoD.ledger.GetRegions() if 'Pass' in r]:
        # Gets the Binning object and some meta information (stored in `_`) that we don't care about
        # The Binning object is needed for constructing the Alphabet objects.
        # If one wanted to be very robust, they could get the binning for `p` as well and check 
        # that the binning is consistent between the two.
        binning_f, _ = twoD.GetBinningFor(f)
        
        # Next we construct the Alphabet objects which all inherit from the Generic2D class.
        # This class constructs and stores RooAbsArg objects (RooRealVar, RooFormulaVar, etc)
        # which represent each bin in the space.

        # First we make a BinnedDistribution which is a collection of RooRealVars built from a starting
        # histogram (`qcd_hists[f]`). These can be set to be constants but, if not, they become free floating
        # parameters in the fit.
        fail_name = 'QCD_'+f
        qcd_f = BinnedDistribution(
                    fail_name, qcd_hists[f],
                    binning_f, constant=False
                )

        # create a BinnedDistribution object corresponding to the smooth QCD MC P/F ratio created earlier (L.66)
        qcd_MC_rpf = BinnedDistribution(
                    'QCD_MC_rpf', smooth_MC_rpf,
                    binning_f, constant=True
                )

        # Next we'll book a 2x1 transfer function to transfer from Fail -> Pass
        qcd_rratio = ParametricFunction(
                        fail_name.replace('Fail','rratio'),
                        binning_f, '(@0+@1*x+@2*x**2)*(1+@3*y)',
                        constraints= {0:{"MIN":-10, "MAX":10}}
                   )

        # We add it to `twoD` so its included when making the RooWorkspace and ledger.
        # We specify the name of the process, the region it lives in, and the object itself.
        # The process is assumed to be a background and colored yellow but this can be changed
        # with optional arguments.
        twoD.AddAlphaObj('QCD',f,qcd_f,title='QCD')

        # Finally, to actually get the qcd_p (pass) distribution, we need to multiply the fail distribution
        # by the QCD MC p/f ratio, and then multiply *that* by the simple polynomial, getting us finally from Fail->Pass
        qcd_intermediate = qcd_f.Multiply(fail_name.replace('Fail','FailTimesMC'), qcd_MC_rpf)
        qcd_p = qcd_intermediate.Multiply(fail_name.replace('Fail','Pass'), qcd_rratio)
        twoD.AddAlphaObj('QCD', p, qcd_p, title='QCD')

    # save the workspace!
    twoD.Save()

def ML_fit(signal):
    '''
    signal [str] = any of the signal masses, as a string. 
    Masses range from [1400,4000], at 200 GeV intervals

    Loads a TwoDAlphabet object from an existing project area, selects
    a subset of objects to run over (a specific signal and TF), makes a sub-directory
    to store the information, and runs the fit in that sub-directory. To make clear
    when a directory/area is being specified vs when a signal is being selected,
    I've redundantly prepended the "subtag" argument with "_area".
    '''

    # the default workspace directory, created in make_workspace(), is called tWfits_deep/
    twoD = TwoDAlphabet('tWfits_deep', 'bstar_deep.json', loadPrevious=True)

    # Create a subset of the primary ledger using the select() method.
    # The select() method takes as a function as its first argument
    # and any args to pass to that function as the remiaining arguments
    # to select(). See _select_signal for how to construct the function.
    subset = twoD.ledger.select(_select_signal, 'signalLH{}'.format(signal))

    # Make card reads the ledger and creates a Combine card from it.
    # The second argument specifices the sub-directory to save the card in.
    # MakeCard() will also save the corresponding Ledger DataFrames as csvs
    # in the sub-directory for later reference/debugging. By default, MakeCard()
    # will reference the base.root workspace in the first level of the project directory
    # (../ relative to the card). However, one can specify another path if a different
    # workspace is desired. Additionally, a different dataset can be supplied via
    # toyData but this requires supplying almost the full Combine card line and
    # is reserved for quick hacks by those who are familiar with Combine cards.
    twoD.MakeCard(subset, 'tW-{}_area'.format(signal))

    # Run the fit! Will run in the area specified by the `subtag` (ie. sub-directory) argument
    # and use the card in that area. Via the cardOrW argument, a different card or workspace can be
    # supplied (passed to the -d option of Combine).
    twoD.MLfit('tW-{}_area'.format(signal),rMin=-1,rMax=20,verbosity=1,extra='--robustFit=1')

def plot_fit(signal):
    '''
    Plots the fits from ML_fit() using 2DAlphabet
    '''
    twoD = TwoDAlphabet('tWfits_deep', 'bstar_deep.json', loadPrevious=True)
    subset = twoD.ledger.select(_select_signal, 'signalLH{}'.format(signal))
    twoD.StdPlots('tW-{}_area'.format(signal), subset)

def perform_limit(signal):
    '''
    Perform a blinded limit. To be blinded, the Combine algorithm (via option `--run blind`)
    will create an Asimov toy dataset from the pre-fit model. Since the TF parameters are meaningless
    in our true "pre-fit", we need to load in the parameter values from a different fit so we have
    something reasonable to create the Asimov toy.
    '''
    # Returns a dictionary of the TF parameters with the names as keys and the post-fit values as dict values.
    twoD = TwoDAlphabet('tWfits_deep', 'bstar_deep.json', loadPrevious=True)

    # GetParamsOnMatch() opens up the workspace's fitDiagnosticsTest.root and selects the rratio for the background
    params_to_set = twoD.GetParamsOnMatch('rratio*', 'tW-{}_area'.format(signal), 'b')
    params_to_set = {k:v['val'] for k,v in params_to_set.items()}

    # The iterWorkspaceObjs attribute stores the key-value pairs in the JSON config
    # where the value is a list. This allows for later access like here so the user
    # can loop over the list values without worrying if the config has changed over time
    # (necessitating remembering that it changed and having to hard-code the list here).
    for signame in twoD.iterWorkspaceObjs['SIGNAME']:
        # signame is going too look like 16_<what we want> so drop the first three characters
        print ('Performing limit for %s'%signame)

        # Make a subset and card as in ML_fit()
        subset = twoD.ledger.select(_select_signal, signame)
        twoD.MakeCard(subset, signame+'_area')
        # Run the blinded limit with our dictionary of TF parameters
        # NOTE: we are running without blinding (blinding seems to cause an issue with the limit plotting script...)
        twoD.Limit(
            subtag=signame+'_area',
            blindData=False,
            verbosity=0,
            setParams=params_to_set,
            condor=False
        )

if __name__ == "__main__":
    make_workspace()

    for sig in range(1400,4200,200):
	ML_fit(str(sig))

    perform_limit('1400')

    '''
    for sig in range(1400,4200,200):
	ML_fit(str(sig))

    perform_limit('1400')

    
    for sig in ['1400','1600','1800']:
	ML_fit(sig)
    '''
   
    #perform_limit('1400')
 
    ''' 
    for sig in ['2400']:
        ML_fit(sig)
        plot_fit(sig)
        #perform_limit(sig)
    '''
