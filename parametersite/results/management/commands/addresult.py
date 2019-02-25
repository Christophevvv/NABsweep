from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum
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
        
        self.processLocalResults(runObject,updateRun)
        self.processGlobalResults(runObject,updateRun)

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
            rv = RunValue(run = r,sweep_parameter = sp,value = params[i]['range'])
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

    def processLocalResults(self,runObject,updateRun):
        p = Processor()
        #create localresult scores for each profile (pandas DataFrame)
        localProfileScores = p.getLocalProfileResults()
        #Get all profiles for which we want to produce results
        profileObjects = []
        for profile in p.getProfiles():
            profileObjects.append(self.getProfile(profile))
        
        for category,dataset,length,raw_score_no_anomaly,\
            raw_score_during_anomaly in p.processLocalResults():
            categoryObject = self.getCategory(category)
            datasetObject = self.getDataset(categoryObject,dataset,length)
            lr = self.getLocalResult(runObject,datasetObject,
                                     raw_score_no_anomaly,
                                     raw_score_during_anomaly)
            if updateRun:
                lr = self._updateLocalResult(lr,raw_score_no_anomaly,
                                             raw_score_during_anomaly)
            #Get the local profile scores for the current dataset    
            scores = localProfileScores[localProfileScores.File\
                                        == str(category+"/"+dataset)]
            #Only 1 row gets returned,containing all scores of all profiles
            assert(scores.shape[0] == 1)
            for profileObject in profileObjects:
                #Get the local result or create a new one if it did not
                #exit yet.
                lrs = self.getLocalResultScore(lr,profileObject,scores)
                if updateRun:
                    self._updateLocalResultScore(lrs,profileObject,scores)

    def getLocalResult(self,runObject,datasetObject,raw_score_no_anomaly,
                       raw_score_during_anomaly):
        # (run,dataset) is unique for LocalResult
        lr = LocalResult.objects.filter(run = runObject,
                                        dataset = datasetObject)
        if lr.count() == 0:
            return self._addLocalResult(runObject,datasetObject,
                                        raw_score_no_anomaly,
                                        raw_score_during_anomaly)
        elif lr.count() == 1:
            return lr.get()
        else:
            pass #unique constraint violated

    def _addLocalResult(self,runObject,datasetObject,raw_score_no_anomaly,
                        raw_score_during_anomaly):
        lr = LocalResult(run = runObject,
                         dataset = datasetObject,
                         pred_error_no_anomaly = raw_score_no_anomaly,
                         pred_error_during_anomaly =\
                         raw_score_during_anomaly)
        lr.save()
        return lr

    def _updateLocalResult(self,lr,raw_score_no_anomaly,
                           raw_score_during_anomaly):
        lr.pred_error_no_anomaly = raw_score_no_anomaly
        lr.pred_error_during_anomaly = raw_score_during_anomaly
        lr.save()
        return lr
            
            
    def getLocalResultScore(self,localResult,profileObject,scores):
        # (local_result,profile) is unique
        lrs = LocalResultScore.objects.filter(local_result = localResult,
                                              profile = profileObject)
        if lrs.count() == 0:
            return self._addLocalResultScore(localResult,profileObject,
                                             scores)
        elif lrs.count() == 1:
            return lrs.get()
        else:
            pass #unique constraint violated

    def _addLocalResultScore(self,localResult,profileObject,scores):
        profilename = profileObject.name
        lrs = LocalResultScore(local_result = localResult,
                               profile = profileObject,
                               score = scores[profilename+"_Score"],
                               true_positives = scores[profilename+"_TP"],
                               true_negatives = scores[profilename+"_TN"],
                               false_positives = scores[profilename+"_FP"],
                               false_negatives = scores[profilename+"_FN"])
        lrs.save()
        return lrs

    def _updateLocalResultScore(self,lrs,profileObject,scores):
        profilename = profileObject.name
        lrs.score = scores[profilename+"_Score"]
        lrs.true_positives = scores[profilename+"_TP"]
        lrs.true_negatives = scores[profilename+"_TN"]
        lrs.false_positives = scores[profilename+"_FP"]
        lrs.false_negatives = scores[profilename+"_FN"]
        lrs.save() #UPDATE
        return lrs

    def processGlobalResults(self,runObject,updateRun):
        #Get all profiles for which we want to produce results
        #profileObjects = []
        p = Processor()
        thresholds = p.getThresholds()
        final_results = p.getFinalResults()
        gr = self.getGlobalResult(runObject)
        for profile in p.getProfiles():
            #profileObjects.append(self.getProfile(profile))            
            profileObject = self.getProfile(profile)
            threshold = thresholds[profileObject.name]['threshold']
            normalized_score = final_results[profileObject.name]
            
            local_scores = LocalResultScore.objects.all().filter(local_result__run = gr.run,
                                                                 profile=profileObject)
            #Aggregate local scores
            score = list(local_scores.aggregate(Sum('score')).values())[0]
            true_positives = list(local_scores.aggregate(Sum('true_positives')).values())[0]
            true_negatives = list(local_scores.aggregate(Sum('true_negatives')).values())[0]
            false_positives = list(local_scores.aggregate(Sum('false_positives')).values())[0]
            false_negatives = list(local_scores.aggregate(Sum('false_negatives')).values())[0]
            grs = self.getGlobalResultScore(gr,
                                            profileObject,
                                            threshold,
                                            normalized_score,
                                            score,
                                            true_positives,
                                            true_negatives,
                                            false_positives,
                                            false_negatives)
            if updateRun:
                self._updateGlobalResultScore(grs,
                                              threshold,
                                              normalized_score,
                                              score,
                                              true_positives,
                                              true_negatives,
                                              false_positives,
                                              false_negatives)

    def getGlobalResult(self,runObject):
        gr = GlobalResult.objects.filter(run = runObject)
        if gr.count() == 0:
            return self._addGlobalResult(runObject)
        elif gr.count() == 1:
            return gr.get()

    def _addGlobalResult(self,runObject):
        lr = LocalResult.objects.all().filter(run = runObject)
        pe_na = list(lr.aggregate(Sum('pred_error_no_anomaly')).values())[0]
        pe_da = list(lr.aggregate(Sum('pred_error_during_anomaly')).values())[0]
        gr = GlobalResult(run = runObject,
                          pred_error_no_anomaly = pe_na,
                          pred_error_during_anomaly = pe_da)
        gr.save()
        return gr

    def getGlobalResultScore(self,gr,profileObject,threshold,
                             normalized_score,score,tp,tn,fp,fn):
        grs = GlobalResultScore.objects.filter(global_result = gr,
                                               profile = profileObject)
        if grs.count() == 0:
            return self._addGlobalResultScore(gr,profileObject,threshold,
                                              normalized_score,score,tp,tn,fp,fn)
        elif grs.count() == 1:
            return grs.get()

    def _addGlobalResultScore(self,gr,profileObject,threshold,
                              normalized_score,score,tp,tn,fp,fn):

        grs = GlobalResultScore(global_result = gr,
                                profile = profileObject,
                                threshold = threshold,
                                normalized_score = normalized_score,
                                score = score,
                                true_positives = tp,
                                true_negatives = tn,
                                false_positives = fp,
                                false_negatives = fn)
        grs.save()
        return grs

    def _updateGlobalResultScore(self,grs,threshold,normalized_score,score,tp,tn,fp,fn):
        grs.threshold = threshold
        grs.normalized_score = normalized_score
        grs.score = score
        grs.true_positives = tp
        grs.true_negatives = tn
        grs.false_positives = fp
        grs.false_negatives = fn
        grs.save()
        return grs
