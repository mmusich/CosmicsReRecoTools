#!/usr/bin/env python

import datetime,time
import os,sys
import string, re
import subprocess
import ConfigParser, json
from optparse import OptionParser

##### method to parse the input file ################################

def ConfigSectionMap(config, section):
    the_dict = {}
    options = config.options(section)
    for option in options:
        try:
            the_dict[option] = config.get(section, option)
            if the_dict[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            the_dict[option] = None
    return the_dict

###### method to create recursively directories on EOS #############

def mkdir_eos(out_path):
    newpath='/'
    for dir in out_path.split('/'):
        newpath=os.path.join(newpath,dir)
        # do not issue mkdir from very top of the tree
        if newpath.find('test_out') > 0:
            p = subprocess.Popen(["cmsMkdir",newpath], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, err) = p.communicate()
            p.wait()

    # now check that the directory exists
    p = subprocess.Popen(["cmsLs",out_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, err) = p.communicate()
    p.wait()
    if p.returncode !=0:
        print out

def split(sequence, size):
##########################    
# aux generator function to split lists
# based on http://sandrotosi.blogspot.com/2011/04/python-group-list-in-sub-lists-of-n.html
# about generators see also http://stackoverflow.com/questions/231767/the-python-yield-keyword-explained
##########################
    for i in xrange(0, len(sequence), size):
        yield sequence[i:i+size] 

#############
class Job:
#############

    def __init__(self, job_id, job_name, applyEXTRACOND, extraCondVect, CMSSW_dir ,the_dir):
###############################
        self.job_id=job_id          
        self.job_name=job_name
        self.applyEXTRACOND    = applyEXTRACOND
        self.extraCondVect     = extraCondVect
    
        self.the_dir=the_dir
        self.CMSSW_dir=CMSSW_dir

        self.output_full_name=self.getOutputBaseName()+"_"+str(self.job_id)

        self.cfg_dir=None
        self.outputCfgName=None
        
        # LSF variables        
        self.LSF_dir=None
        self.output_LSF_name=None

        self.lfn_list=list()      

    def __del__(self):
###############################
        del self.lfn_list

    def setEOSout(self,theEOSdir):    
###############################
        self.OUTDIR = theEOSdir
          
    def getOutputBaseName(self):
########################    
        return "myTest_"+self.job_name
        
    def createTheCfgFile(self,lfn):
###############################
        
        # write the cfg file 
        self.cfg_dir = os.path.join(self.the_dir,"cfg")
        if not os.path.exists(self.cfg_dir):
            os.makedirs(self.cfg_dir)

        self.outputCfgName=self.output_full_name+"_cfg.py"
        fout=open(os.path.join(self.cfg_dir,self.outputCfgName),'w+b')

        ## Reco + TkAlCosmics0T AlCa Stream 
        template_cfg_file = os.path.join(self.the_dir,"step1_RAW2DIGI_RECO_ALCA.py")
        
        fin = open(template_cfg_file)

        for line in fin.readlines():

            if 'True' in self.applyEXTRACOND:
                if 'APPEND OF EXTRA CONDITIONS' in line:
                    for element in self.extraCondVect :
                    #print element[0],element[1],element[2]
                        
                        fout.write(" \n")
                        fout.write("process.conditionsIn"+element[0]+"= CalibTracker.Configuration.Common.PoolDBESSource_cfi.poolDBESSource.clone( \n")
                        fout.write("     connect = cms.string('"+element[1]+"'), \n")
                        fout.write("     toGet = cms.VPSet(cms.PSet(record = cms.string('"+element[0]+"'), \n")
                        fout.write("                                tag = cms.string('"+element[2]+"') \n")
                        fout.write("                                ) \n")
                        fout.write("                       ) \n")
                        fout.write("     ) \n")
                        fout.write("process.prefer_conditionsIn"+element[0]+" = cms.ESPrefer(\"PoolDBESSource\", \"conditionsIn"+element[0]+"\") \n \n") 
                        
            if line.find("FILESOURCETEMPLATE")!=-1:
                lfn_with_quotes = map(lambda x: "\'"+x+"\'",lfn)                   
                #print "["+",".join(lfn_with_quotes)+"]"
                line=line.replace("FILESOURCETEMPLATE","["+",".join(lfn_with_quotes)+"]") 
            if line.find("OUTFILETEMPLATE")!=-1:
                line=line.replace("OUTFILETEMPLATE",self.output_full_name+".root")     
            fout.write(line)    
      
        fout.close()                
                          
    def createTheLSFFile(self):
###############################

       # directory to store the LSF to be submitted
        self.LSF_dir = os.path.join(self.the_dir,"LSF")
        if not os.path.exists(self.LSF_dir):
            os.makedirs(self.LSF_dir)

        self.output_LSF_name=self.output_full_name+".lsf"
        fout=open(os.path.join(self.LSF_dir,self.output_LSF_name),'w')
    
        job_name = self.output_full_name

        log_dir = os.path.join(self.the_dir,"log")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        fout.write("#!/bin/sh \n") 
        fout.write("#BSUB -L /bin/sh\n")       
        fout.write("#BSUB -J "+job_name+"\n")
        fout.write("#BSUB -o "+os.path.join(log_dir,job_name+".log")+"\n")
        fout.write("#BSUB -q cmscaf1nd \n")
        fout.write("JobName="+job_name+" \n")
        fout.write("OUT_DIR="+self.OUTDIR+" \n")
        fout.write("LXBATCH_DIR=`pwd` \n") 
        fout.write("cd "+os.path.join(self.CMSSW_dir,"src")+" \n")
        fout.write("eval `scram runtime -sh` \n")
        fout.write("cd $LXBATCH_DIR \n") 
        fout.write("cmsRun "+os.path.join(self.cfg_dir,self.outputCfgName)+" \n")
        fout.write("ls -lh . \n")
        fout.write("for RootOutputFile in $(ls *root |grep myTest ); do xrdcp -f ${RootOutputFile}  ${OUT_DIR}/${RootOutputFile} ; done \n")
        fout.write("for TxtOutputFile in $(ls *txt ); do xrdcp -f ${TxtOutputFile}  ${OUT_DIR}/${TxtOutputFile} ; done \n")

        fout.close()

    def getOutputFileName(self):
############################################
        return os.path.join(self.OUTDIR,self.output_full_name+".root")
        
    def submit(self):
###############################        
        print "submit job", self.job_id
        job_name = self.output_full_name
        submitcommand1 = "chmod u+x " + os.path.join(self.LSF_dir,self.output_LSF_name)
        child1  = os.system(submitcommand1)
        submitcommand2 = "bsub < "+os.path.join(self.LSF_dir,self.output_LSF_name)
        child2  = os.system(submitcommand2)

##############################################
def main():
##############################################

    # CMSSW section
    input_CMSSW_BASE = os.environ.get('CMSSW_BASE')
    AnalysisStep_dir = os.path.join(input_CMSSW_BASE,"src")
    lib_path = os.path.abspath(AnalysisStep_dir)
    sys.path.append(lib_path)

    ## N.B.: this is dediced here once and for all
    #from sources_cff import CosmicsSrc
    from all_cosmics_cff import CosmicsSrc
    srcFiles        = [CosmicsSrc]

    desc="""This is a description of %prog."""
    parser = OptionParser(description=desc,version='%prog version 0.1')
    parser.add_option('-s','--submit',  help='job submitted', dest='submit', action='store_true', default=False)
    parser.add_option('-j','--jobname', help='task name', dest='taskname', action='store', default='')
    parser.add_option('-i','--input',help='set input configuration (overrides default)',dest='inputconfig',action='store',default=None)
    (opts, args) = parser.parse_args()

    now = datetime.datetime.now()
    #t = now.strftime("test_%Y_%m_%d_%H_%M_%S_DATA_ReReco_")
    t = "test_CRUZET17_DATA_ReReco_"
    t+=opts.taskname
    
    USER = os.environ.get('USER')
    eosdir=os.path.join("/eos/cms/store/group/alca_trackeralign/",USER,"test_out",t)
    if(opts.submit):
        mkdir_eos(eosdir)

    #### Initialize all the variables

    jobName         = None
    applyEXTRACOND  = None
    extraCondVect   = None      
     
    ConfigFile = opts.inputconfig
    
    if ConfigFile is not None:

        print "********************************************************"
        print "* Parsing from input file:", ConfigFile," "
        
        config = ConfigParser.ConfigParser()
        config.read(ConfigFile)

        #print  config.sections()

        # please notice: since in principle one wants to run on several different samples simultaneously,
        # all these inputs are vectors
        jobName          = [ConfigSectionMap(config,"Job")['jobname']+"_"+opts.taskname] 
        applyEXTRACOND   = [ConfigSectionMap(config,"Conditions")['applyextracond']]
        value            = ConfigSectionMap(config,"Conditions")['extracondvect']
        #print "apply:",applyEXTRACOND[0]," value:",value
        # some magic is need to write correctly the vector of vectors...
        if 'True' in applyEXTRACOND[0]:
            if "|" in value:
                bunch            = value.split('|')
                extraCondVect    = [[bunch[0].split(','),bunch[1].split(',')]]
            else:
                extraCondVect    = [[value.split(',')]]
        else:
            extraCondVect = [['None', 'None', 'None']]
    else :

        print "********************************************************"
        print "* Parsing from command line                            *"
        print "********************************************************"
          
        jobName         = ['MinBiasQCD_CSA14Ali_CSA14APE']      
        applyEXTRACOND  = ['False']
        extraCondVect   = [[('SiPixelTemplateDBObjectRcd','frontier://FrontierProd/CMS_COND_31X_PIXEL','SiPixelTemplates38T_2010_2011_mc'),
                            ('SiPixelQualityFromDBRcd','frontier://FrontierProd/CMS_COND_31X_PIXEL','SiPixelQuality_v20_mc')]]
     
    # start loop on samples

    # print some of the configuration
    
    print "********************************************************"
    print "* Configuration info *"
    print "********************************************************"
    print "- submitted   : ",opts.submit
    print "- Jobname     : ",jobName                    
    print "- extraCond?  : ",applyEXTRACOND
    print "- conditions  : ",extraCondVect                   
   
    for iConf in range(len(srcFiles)):

    # for hadd script
        scripts_dir = os.path.join(AnalysisStep_dir,"scripts")
        if not os.path.exists(scripts_dir):
            os.makedirs(scripts_dir)
        hadd_script_file = os.path.join(scripts_dir,jobName[iConf])
        fout = open(hadd_script_file,'w')

        output_file_list1=list()      
        output_file_list2=list()
        output_file_list2.append("hadd ")
            
        for jobN,theSrcFiles in enumerate(split(srcFiles[iConf],1)):
            #print jobN
            aJob = Job(jobN,jobName[iConf], applyEXTRACOND[iConf],extraCondVect[iConf],input_CMSSW_BASE,AnalysisStep_dir)
            
            aJob.setEOSout(eosdir)
            aJob.createTheCfgFile(theSrcFiles)
            aJob.createTheLSFFile()

            output_file_list1.append("xrdcp "+aJob.getOutputFileName()+" . \n")
            if jobN == 0:
                output_file_list2.append(aJob.getOutputBaseName()+".root ")
            output_file_list2.append(os.path.split(aJob.getOutputFileName())[1]+" ")    
   
            if opts.submit:
                aJob.submit()
            del aJob

        fout.writelines(output_file_list1)
        fout.writelines(output_file_list2)

        fout.close()
        del output_file_list1
        
if __name__ == "__main__":        
    main()


   
