from django.core.management.base import BaseCommand
from django.db import transaction
from results.models import *
import json

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

    @transaction.atomic
    def addresult(self,params):
        #Check if parameters are known, otherwise add them
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
        #Check if a sweep for this parameterset exists
        sweepObject = None
        for sweep in Sweep.objects.filter(nr_params=len(params)):
            sp = SweepParameter.objects.filter(sweep__id=sweep.id)
            assert(sp.count() == len(params)) #otherwise there is something wrong with the sweep object...
            found = True
            for p in paramObjects:
                if(not sp.filter(parameter__id = p.id).exists()):
                    found = False
            if(found):
                sweepObject = sweep
                break
        if(sweepObject == None): #No sweep found, create a new one
            sweepObject = self._addSweep(paramObjects)

        #Get runs for given sweep to see if we already performed this value combination
        runObject = None
        updateRun = False
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
                runObject = run
                print("A run with given parameter values was found, results will be UPDATED.")
                updateRun = True
                break
        if(runObject == None): #No run found with these parameter value combination, create new one
            runObject = self._addRun(sweepObject,paramObjects,params)
        
            
    def _addParameter(self,group,name):
        p = Parameter(group=group,name=name)
        p.save()
        return p

    def _addCategory(self,name):
        c = Category(name=name)
        c.save()
        return c

    def _addDataset(self,category,name):
        d = Dataset(category=category,name=name)
        d.save()
        return d

    def _addSweep(self,paramObjects):
        #Create the sweep
        s = Sweep(nr_params = len(paramObjects))
        s.save()
        #link parameters to this sweep
        for param in paramObjects:
            sp = SweepParameter(sweep=s,parameter=param)
            sp.save()
        return s

    def _addRun(self,sweepObject,paramObjects,params):
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
        
