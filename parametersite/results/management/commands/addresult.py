from django.core.management.base import BaseCommand
from django.db import transaction
from results.models import *
import json
from .process_results import Processor

class Command(BaseCommand):
    args = '<addresult --parametersFile file.json>'
    help = 'Add result of parameter run to database.'

    def add_arguments(self,parser):
        parser.add_argument(
            '--parametersFile',
            dest='parametersFile',
            required=True,
            help='File that contains the parameters + values for this run'
            )
        
    def handle(self, *args, **options):
        paramFile = options['parametersFile']
        print(paramFile)
        try:
            params_json = json.load(open(paramFile,'r'))
        except FileNotFoundError:
            print("File not found: " + str(paramFile))
            exit(1)
        print(params_json)
        self.addresult(params_json)

    #Make sure all database operations succeed. Else roll back everything
    @transaction.atomic
    def addresult(self,params):
        #Check if parameters are known, otherwise add them
        paramObjects = self.getParameters(params)
        #Check if a sweep for this parameterset exists
        sweepObject = self.getSweep(paramObjects)
        #Get runs for given sweep to see if we already performed this value combination
        runObject,updateRun = self.getRun(sweepObject,paramObjects,params)
        
        self.addLocalResults(runObject,updateRun)

    def getParameters(self,params):
        ''' Get parameter objects or create them if they did not exist '''
        paramObjects = []
        for param in params:
            p = Parameter.objects.filter(group=param['group']).filter(name=param['name'])
            if(len(p) == 0):
                p = self._addParameter(group=param['group'],name=param['name'])
            elif(len(p) == 1):
                p = p.get()
            else:
                pass #unique constraint violated
            paramObjects.append(p)
        return paramObjects
            
    def _addParameter(self,group,name):
        ''' Create new parameter '''
        p = Parameter(group=group,name=name)
        p.save()
        return p

    def getCategory(self,name):
        c = Category.objects.filter(name = name)
        if(c.count() == 0):
            return self._addCategory(name)
        elif(c.count() == 1):
            return c.get()
        else:
            pass #unique constraint violation

    def _addCategory(self,name):
        ''' Create new category '''
        c = Category(name=name)
        c.save()
        return c

    def getDataset(self,category,name,length):
        d = Dataset.objects.filter(category=category).filter(name=name)
        if(d.count() == 0):
            return self._addDataset(category,name,length)
        elif(d.count() == 1):
            return d.get()
        else:
            pass #unique constraint violation

    def _addDataset(self,category,name,length):
        ''' Create new dataset '''
        d = Dataset(category=category,name=name,length=length)
        d.save()
        return d

    def getSweep(self,paramObjects):
        for sweep in Sweep.objects.filter(nr_params=len(paramObjects)):
            sp = SweepParameter.objects.filter(sweep__id=sweep.id)
            assert(sp.count() == len(paramObjects)) #otherwise there is something wrong with the sweep object...
            found = True
            for p in paramObjects:
                if(not sp.filter(parameter__id = p.id).exists()):
                    found = False
            if(found):
                return sweep
        #No sweep found, create new one
        return self._addSweep(paramObjects)
    
    def _addSweep(self,paramObjects):
        ''' Create new Sweep + link parameters to this sweep'''
        #Create the sweep
        s = Sweep(nr_params = len(paramObjects))
        s.save()
        #link parameters to this sweep
        for param in paramObjects:
            sp = SweepParameter(sweep=s,parameter=param)
            sp.save()
        return s

    def getRun(self,sweepObject,paramObjects,params):
        for run in Run.objects.filter(sweep__id = sweepObject.id):
            rv = RunValue.objects.filter(run__id = run.id)
            assert(rv.count() == len(params))
            found = True
            for param in params:
                q = rv.filter(sweep_parameter__parameter__name = param['name'])
                q = q.filter(sweep_parameter__parameter__group = param['group'])
                if(not q.filter(value=param['range']).exists()):
                    found = False
            if(found):
                print("A run with given parameter values was found, results will be UPDATED.")
                return run,True
        #No run found with these parameter value combination, create new one
        return self._addRun(sweepObject,paramObjects,params),False
        
    def _addRun(self,sweepObject,paramObjects,params):
        ''' Create new run + link parameter values to this run '''
        #Create the run
        r = Run(sweep=sweepObject)
        r.save()
        assert(len(paramObjects) == len(params))
        #link parameter values to this run
        for i in range(0,len(params)):
            sp = SweepParameter.objects.get(parameter__id = paramObjects[i].id, sweep__id=sweepObject.id)
            rv = RunValue(run = r,sweep_parameter = sp,value = float(params[i]['range']))
            rv.save()
        return r

    def getProfile(self,profile):
        p = Profile.objects.filter(name=profile[0])
        if(p.count() == 0):
            return self._addProfile(profile)
        elif(p.count() == 1):
            return p.get()
        else:
            pass #unique constraint violation

    def _addProfile(self,profile):
        p = Profile(name=profile[0],
                    tp_weight=profile[1]['tpWeight'],
                    fp_weight=profile[1]['fpWeight'],
                    tn_weight=profile[1]['tnWeight'],
                    fn_weight=profile[1]['fnWeight'])
        p.save()
        return p

    def addLocalResults(self,runObject,updateRun):
        p = Processor()
        #create localresult scores for each profile (pandas DataFrame)
        localProfileScores = p.getLocalProfileResults()
        profileObjects = []
        for profile in p.getProfiles():
            profileObjects.append(self.getProfile(profile))
        
        for category,dataset,length,raw_score_no_anomaly,\
            raw_score_during_anomaly in p.processLocalResults():
            categoryObject = self.getCategory(category)
            datasetObject = self.getDataset(categoryObject,dataset,length)
            #create local result
            if(updateRun):
                #get the original LocalResult
                lr = LocalResult.objects.filter(run__id = runObject.id,
                                                dataset__id = datasetObject.id)
                assert(lr.count() == 1)
                lr.update(pred_error_no_anomaly=raw_score_no_anomaly,
                          pred_error_during_anomaly=raw_score_during_anomaly)
                lr = lr.get()
            else:
                lr = LocalResult(run=runObject,dataset=datasetObject,
                                 pred_error_no_anomaly=raw_score_no_anomaly,pred_error_during_anomaly=raw_score_during_anomaly)
                lr.save()
            localProfileScores_dataset = localProfileScores[localProfileScores.File == str(category+"/"+dataset)]
            assert(localProfileScores_dataset.shape[0] == 1)
            for profileObject in profileObjects:
                #HOW ABOUT UPDATE?
                #idea: make getLocalResultScore with call to _add if not
                #exist, do update if update flag set
                #this way even though we already did this, we can
                #add new profiles.
                profilename = profileObject.name
                lrs = LocalResultScore(local_result = lr,
                                       profile = profileObject,
                                       score = localProfileScores_dataset[profilename+"_Score"],true_positives=localProfileScores_dataset[profilename+"_TP"],true_negatives=localProfileScores_dataset[profilename+"_TN"],false_positives=localProfileScores_dataset[profilename+"_FP"],false_negatives=localProfileScores_dataset[profilename+"_FN"])
                lrs.save()
                

                
            
            

