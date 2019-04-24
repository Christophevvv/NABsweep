#Perform a paramsweep in python
import argparse
import os
import json
import itertools
import subprocess
import copy
import logging


def main(args):
    with open(args.sweepFile) as f:
        params = json.load(f)
    ps = ParameterSweep(params)
    #ps.info()
    ps.run()


class ParameterSweep:
    def __init__(self,params):
        self.params = params
        #print(os.path.dirname(os.path.abspath(__file__)))
        self.NAB = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),params['general']['NAB_location']))
        self.django = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),params['general']['django_location']))
        self.config_location = os.path.join(self.NAB,params['general']['config_location'])
        self.output_config_location = os.path.join(self.NAB,params['general']['output_config_location'])
        self.output_parameter_values = os.path.join(self.django,params['general']['output_parameter_values'])
        self.verbosity = params['verbosity']
        self.nr_sweeps = len(params['sweeps'])
        logging.basicConfig(filename='paramsweep.log',format='%(asctime)s %(message)s',level=logging.DEBUG)
        
        if self.verbosity > 0:
            print("VERBOSE OUTPUT BEING GENERATED:")
            self.info()

    def run(self):
        ''' Start parameter sweep '''
        sweeps = self.params['sweeps']
        for sweep in sweeps:
            if self.verbosity > 0:
                self.printSweepInfo(sweep)
            self.runSweep(sweep)

    def runSweep(self,sweep):
        ''' Geral run sweep. Delegates to runSingleSweep or runMultiSweep '''
        multi_parameter = sweep['MultiParameter']
        if multi_parameter:
            #linear = sweep['linear']
            self.runMultiSweep(sweep)
        else:
            self.runSingleSweep(sweep)

    def runSingleSweep(self,sweep):
        ''' Run sweep where only one parameter varies at a time '''
        parameters = sweep['parameters']
        for parameter in parameters:
            #Reset config for every new parameter
            config = self.loadConfig(self.config_location)            
            for value in parameter['range']:
                #write parameter + value to config
                self.writeToConfig(config,parameter,value)
                self.saveConfig(config,self.output_config_location)
                #write parameter + value to parameter_values
                self.newParameterValues()
                self.writeToParameterValues(copy.copy(parameter),value)
                self.saveParameterValues(self.output_parameter_values)
                if self.runNAB():
                    self.addResult()


    def runMultiSweep(self,sweep):
        parameters = sweep['parameters']        
        config = self.loadConfig(self.config_location)
        linear_parameters = {}
        nonlinear_parameters = []
        for parameter in parameters:
            if "linear" in parameter and parameter['linear'] == True:
                if "linear_group" in parameter:
                    if parameter["linear_group"] in linear_parameters:
                        linear_parameters[parameter["linear_group"]].append(parameter)
                    else:
                        linear_parameters[parameter["linear_group"]] = [parameter]
                else:
                    if "nameless_group" in linear_parameters:
                        linear_parameters["nameless_group"].append(parameter)
                    else:
                        linear_parameters["nameless_group"] = [parameter]
            else:
                nonlinear_parameters.append(parameter)
        print(linear_parameters)
        print(nonlinear_parameters)
        for linear_group in linear_parameters:
            assert(self._checkLength(linear_parameters[linear_group])),"parameters of the same linear group should have the same length!"
        #nr_groups = len(linear_parameters)
        product = []
        for group in linear_parameters:
            for entry in linear_parameters[group]:
                group_length = len(entry["range"])
                break
            if product == []:
                product = list(range(group_length))
            else:
                product = list(itertools.product(product,
                                                 list(range(group_length))))
        #add nonlinear paramters to product
        for parameter in nonlinear_parameters:
            if product == []:
                product = parameter['range']
            else:
                product = list(itertools.product(product,
                                                 parameter['range']))

        print("The product of this parameter set will require " + str(len(product)) + " runs.")
        k = 1
        for combination in product:
            print("run " + str(k) + "/" + str(len(product)))
            k += 1
            run_values = self._tupleToArray(combination)
            #assert(len(run_values) == len(params['sweeps']))
            self.newParameterValues()
            i = 0
            for group in linear_parameters:
                for parameter in linear_parameters[group]:
                    self.writeToConfig(config,parameter,parameter["range"][run_values[i]])
                    self.writeToParameterValues(copy.copy(parameter),parameter["range"][run_values[i]])
                i += 1            
            for j in range(len(nonlinear_parameters)):                
                self.writeToConfig(config,nonlinear_parameters[j],run_values[i+j])
                self.writeToParameterValues(copy.copy(nonlinear_parameters[j]),run_values[i+j])
            self.saveConfig(config,self.output_config_location)
            #write parameter + value to parameter_values
            self.saveParameterValues(self.output_parameter_values)
            if self.runNAB():
                self.addResult()
            

    def _checkLength(self,array):
        ''' Check if all entries in the array have the same length. If not return False '''
        length = None
        for entry in array:
            if length == None:
                length = len(entry["range"])
            else:
                if length != len(entry["range"]):
                    return False
        return True
        
                    
    # def runMultiSweep(self,sweep):
    #     parameters = sweep['parameters']        
    #     config = self.loadConfig(self.config_location)

    #     linear_parameters = []
    #     nonlinear_parameters = []
    #     for parameter in parameters:
    #         if parameter['linear'] == True:
    #             linear_parameters.append(parameter)
    #         else:
    #             nonlinear_parameters.append(parameter)
    #     length = 0
    #     for parameter in linear_parameters:
    #         if length == 0:
    #             length = len(parameter['range'])
    #         else:
    #             #If assert fails, we can't do a linear sweep.
    #             #Length has to match             
    #             assert(length == len(parameter['range']))
    #     product = []
    #     for parameter in nonlinear_parameters:
    #         if product == []:
    #             product = parameter['range']
    #         else:
    #             product = list(itertools.product(product,
    #                                              parameter['range']))
    #     if length > 0 and len(product) > 0:
    #         if self.verbosity > 0:
    #             print("The product of this parameter set will require " + str(len(product)*length) + " runs.")
    #         for i in range(length):
    #             #take i'th entry in range of each parameter and perform a run:               
    #             for combination in product:
    #                 if self.verbosity > 0:
    #                     print("Running new combination")
    #                 #run_values holds the value for each parameter in the order in which params are listed
    #                 run_values = self._tupleToArray(combination)
    #                 #assert(len(run_values) == len(params['sweeps']))
    #                 self.newParameterValues()
    #                 for j in range(len(nonlinear_parameters)):                
    #                     self.writeToConfig(config,nonlinear_parameters[j],run_values[j])
    #                     self.writeToParameterValues(copy.copy(nonlinear_parameters[j]),run_values[j])
    #                 #linear parameters
    #                 for l_parameter in linear_parameters:                            
    #                     self.writeToConfig(config,l_parameter,l_parameter['range'][i])
    #                     self.writeToParameterValues(copy.copy(l_parameter),
    #                                                 l_parameter['range'][i])
    #                 self.saveConfig(config,self.output_config_location)
    #                 #write parameter + value to parameter_values
    #                 self.saveParameterValues(self.output_parameter_values)
    #                 if self.runNAB():
    #                     self.addResult()
                    
    #     elif length > 0 and len(product) == 0:
    #         if self.verbosity > 0:
    #             print("The product of this parameter set will require " + str(length) + " runs.")            
    #         for i in range(length):
    #             self.newParameterValues()
    #             #take i'th entry in range of each parameter and perform a run:
    #             for l_parameter in linear_parameters:
    #                 self.writeToConfig(config,l_parameter,l_parameter['range'][i])
    #                 self.writeToParameterValues(copy.copy(l_parameter),
    #                                             l_parameter['range'][i])
    #             self.saveConfig(config,self.output_config_location)
    #             #write parameter + value to parameter_values
    #             self.saveParameterValues(self.output_parameter_values)
    #             if self.runNAB():
    #                 self.addResult()
    #     elif length == 0 and len(product) > 0:
    #         if self.verbosity > 0:
    #             print("The product of this parameter set will require " + str(len(product)) + " runs.")            
    #         for combination in product:
    #             if self.verbosity > 0:
    #                 print("Running new combination")
    #             #run_values holds the value for each parameter in the order in which params are listed
    #             run_values = self._tupleToArray(combination)
    #             #assert(len(run_values) == len(params['sweeps']))
    #             self.newParameterValues()
    #             for j in range(len(nonlinear_parameters)):                
    #                 self.writeToConfig(config,nonlinear_parameters[j],run_values[j])
    #                 self.writeToParameterValues(copy.copy(nonlinear_parameters[j]),run_values[j])
    #             self.saveConfig(config,self.output_config_location)
    #             #write parameter + value to parameter_values
    #             self.saveParameterValues(self.output_parameter_values)
    #             if self.runNAB():
    #                 self.addResult()
    #     else:
    #         print("No parameters defined in this sweep")

        # if linear:
        #     length = None
        #     #CHECK IF LENGTHS MATCH
        #     for parameter in parameters:
        #         if length == None:
        #             length = len(parameter['range'])
        #         else:
        #             #If assert fails, we can't do a linear sweep. Length has to match             
        #             assert(length == len(parameter['range']))
                           
        #     for i in range(length):
        #         self.newParameterValues()
        #         #take i'th entry in range of each parameter and perform a run:
        #         for parameter in parameters:
        #             self.writeToConfig(config,parameter,parameter['range'][i])
        #             self.writeToParameterValues(copy.copy(parameter),parameter['range'][i])
        #         self.saveConfig(config,self.output_config_location)
        #         #write parameter + value to parameter_values
        #         self.saveParameterValues(self.output_parameter_values)
        #         self.runNAB()
        #         self.addResult()
        #     return #Do not run anything else
        # #ELSE: NOT LINEAR (IMPLICIT)
        # #Construct the product of all parameter values
        # product = None
        # for parameter in parameters:
        #     if product == None:
        #         product = parameter['range']
        #     else:
        #         product = list(itertools.product(product,parameter['range']))
        # if self.verbosity > 0:
        #     print("The product of this parameter set will require " + str(len(product)) + " runs.")
        # for combination in product:
        #     if self.verbosity > 0:
        #         print("Running new combination")
        #     #run_values holds the value for each parameter in the order in which params are listed
        #     run_values = self._tupleToArray(combination)
        #     #assert(len(run_values) == len(params['sweeps']))
        #     self.newParameterValues()
        #     for i in range(len(parameters)):                
        #         self.writeToConfig(config,parameters[i],run_values[i])
        #         self.writeToParameterValues(copy.copy(parameters[i]),run_values[i])                
        #     self.saveConfig(config,self.output_config_location)
        #     #write parameter + value to parameter_values
        #     self.saveParameterValues(self.output_parameter_values)
        #     self.runNAB()
        #     self.addResult()                

    def _tupleToArray(self,t):
        ''' Turn tuple of tuples into an array.
        example: ((1,2),3) -> [1,2,3] '''
        if type(t) == tuple:
            result = []
            for i in t:
                result.extend(self._tupleToArray(i))
            return result
        else:
            return [t]

    def runNAB(self):
        ''' Run NAB as a different process and wait for it to return '''
        try:
            print(subprocess.check_output([self.params['general']['python2'],"run.py","-d","null","numenta","-m",str(self.params['general']['output_config_location']),"--skipConfirmation"],cwd=self.NAB))#,stderr=subprocess.STDOUT,shell=True))
        except subprocess.CalledProcessError as e:
            print("Error occured while running following command: " + str(e.cmd))
            print(e.output)
            logging.warning("Error occured while running following command: " + str(e.cmd) + ": " + str(e.output))
            logging.warning("This happened for parameter values: " + str(self.parameter_values))
            return False
            #print(subprocess.check_output(["echo","test"],stderr=subprocess.STDOUT))#,stderr=subprocess.STDOUT,shell=True))
        return True

    def addResult(self):
        ''' Call addResult in django project that adds the current run to database '''
        try:
            print(subprocess.check_output([self.params['general']['python3'],os.path.join(self.django,"manage.py"),"addresult","--parametersFile",self.output_parameter_values]))
        except subprocess.CalledProcessError as e:
            print("Error occured while running following command: " + str(e.cmd))
            print(e.output)

    def loadConfig(self,location):
        ''' Load and return config at given location '''
        with open(location) as infile:
            return json.load(infile)
            
    def saveConfig(self,config,location):
        ''' Save config to given location '''
        with open(location,'w') as outfile:
            json.dump(config,outfile)
            
    def writeToConfig(self,config,parameter,value):
        ''' Write parameter + value to config (=json object) '''
        group = parameter['group']
        if group == "":
            config['numenta']['modelConfig']['modelParams'][parameter['name']] = value
        elif group in ['spParams','tmParams']:
            config['numenta']['modelConfig']['modelParams'][group][parameter['name']] = value
        else: #encoder
            if group == 'valueEncoder':
                config['numenta']['modelConfig']['modelParams']['sensorParams']['encoders']['value'][parameter['name']] = value
            elif group == 'timestampEncoder':
                config['numenta']['modelConfig']['modelParams']['sensorParams']['encoders']['timestamp_timeOfDay'][parameter['name']] = value
            else:
                config['numenta']['modelConfig']['modelParams']['sensorParams']['encoders'][group][parameter['name']] = value

    def saveParameterValues(self,location):
        print(self.parameter_values)
        with open(location,'w') as outfile:
            json.dump(self.parameter_values,outfile)

    def newParameterValues(self):
        self.parameter_values = []

    def writeToParameterValues(self,parameter,value):
        parameter['range'] = value #CHECK FOR CHANGE IN CALLBACK
        self.parameter_values.append(parameter)
            
    def printSweepInfo(self,sweep):
        print("Starting new sweep.")
        #TODO: verbose output

            
    def info(self):
        ''' Print info about parameter sweep '''
        print("ParameterSweepInfo:")
        print("------------GENERAL-------------")
        print("NAB folder: " + str(self.NAB))
        print("Django folder: " + str(self.django))
        print("Original config location: " + str(self.config_location))
        print("Output config location: " + str(self.output_config_location))
        print("Output parameter values location: " + str(self.output_parameter_values))
        print("------------SWEEPS--------------")
        print("Number of sweeps: " + str(self.nr_sweeps))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-f","--sweepFile",
                        default="testparams.json",
                        help="The json holding the parameters and values over which to sweep")
    parser.add_argument("-s","--singleParameter",
                        default=True,
                        help="Do a single parameter sweep. (not all combinations of param values)")
    args = parser.parse_args()
    main(args)
