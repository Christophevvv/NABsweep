#Processes results for given parameter
import os
import math
import pandas
import json

class Processor:
  def __init__(self,resultsDir ="results",detectorName="numenta",
               configDir = "config", profilesFile="profiles.json"):
    self.resultsDir = resultsDir
    self.detectorName = detectorName
    self.configDir = configDir
    self.profilesFile = profilesFile
    self.probationPercent = 0.15
    #simplified absolute path of NAB
    self.NABDir = os.path.realpath(os.path.join(os.path.dirname(__file__),'..','..','..','..','NAB'))
    
  def _getProbationaryLength(self, numRows):
    return int(min(
      math.floor(self.probationPercent * numRows),
      self.probationPercent * 5000
    ))
    
  def absoluteFilePaths(self,directory):
    """Given directory, gets the absolute path of all files within.
    
    @param  directory   (string)    Directory name.

    @return             (iterable)  All absolute filepaths within directory.
    """
    for dirpath,_,filenames in os.walk(directory):
      filenames = [f for f in filenames if not f[0] == "."]
      for f in filenames:
        yield os.path.abspath(os.path.join(dirpath, f))

  def getRelativePath(self,srcRoot,srcPath):
    return srcPath[srcPath.index(srcRoot)+len(srcRoot):]\
      .strip(os.path.sep).replace(os.path.sep, "/")
  
  def processLocalResults(self):
    resultsDetectorDir = os.path.join(self.NABDir,self.resultsDir, self.detectorName)

    filePaths = self.absoluteFilePaths(resultsDetectorDir)
    dataSets = [(path,pandas.io.parsers.read_csv(path,header=0, parse_dates=[0])) for path in filePaths if ".csv" in path]
    
    for dataset in dataSets:
      relativePath = self.getRelativePath(resultsDetectorDir,dataset[0])
      data = dataset[1]

      raw_score_no_anomaly = 0 
      raw_score_during_anomaly = 0
      path = relativePath.split("/")
      if(len(path) == 2):
        group = path[0]
        file = path[1][len(self.detectorName+"_"):]
      else:
        continue
      probationaryLength = self._getProbationaryLength(len(data))
      #throw away all points before probation period
      data = data[probationaryLength:]
      raw_score_no_anomaly = data[data.label == 0][['raw_score']].sum(axis=0)
      raw_score_during_anomaly = data[data.label == 1][['raw_score']].sum(axis=0)
      # for i,row in data.iterrows():
      #   if i >= probationaryLength:
      #     if row["label"] == 0:
      #       raw_score_no_anomaly += row["raw_score"]
      #     else:
      #       raw_score_during_anomaly += row["raw_score"]
      #print(raw_score_no_anomaly)
      #print(raw_score_during_anomaly)

      yield group,file,len(data),raw_score_no_anomaly,raw_score_during_anomaly

  def getProfiles(self):
    profilePath = os.path.join(self.NABDir,self.configDir,self.profilesFile)
    try:
      profiles = json.load(open(profilePath,'r'))
    except FileNotFoundError:
      print("File not found: " + str(profilePath))
      exit(1)
    #print(profiles)
    for profile in profiles:
      yield profile,profiles[profile]['CostMatrix']


  def getLocalProfileResults(self):
    first = True
    df = None
    for profile in self.getProfiles():
      filename = self.detectorName + "_" + profile[0] + "_scores.csv"
      profileResultPath = os.path.join(self.NABDir,
                                       self.resultsDir,
                                       self.detectorName,
                                       filename)
      column_names = ['Detector','Profile','File','Threshold',
                      profile[0]+'_Score',profile[0]+'_TP',
                      profile[0]+'_TN',profile[0]+'_FP',
                      profile[0]+'_FN','Total_Count']
      profile_df = pandas.read_csv(profileResultPath,names=column_names)[1:-1]
      if first:
        keep_column = ['File',profile[0]+'_Score',profile[0]+'_TP',
                      profile[0]+'_TN',profile[0]+'_FP',
                      profile[0]+'_FN']
        first=False
        df = profile_df[keep_column]
      else:
        keep_column = [profile[0]+'_Score',profile[0]+'_TP',
                      profile[0]+'_TN',profile[0]+'_FP',
                      profile[0]+'_FN']
        df = df.join(profile_df[keep_column])
    return df
      

  def getThresholds(self):
    thresholdsPath = os.path.join(self.NABDir,
                                  self.configDir,
                                  "thresholds.json")
    try:
      return json.load(open(thresholdsPath,'r'))[self.detectorName]
    except FileNotFoundError:
      print("File not found: " + str(thresholdsPath))
      exit(1)    

  def getFinalResults(self):
    finalresultPath = os.path.join(self.NABDir,
                                   self.resultsDir,
                                   "final_results.json")
    try:
      return json.load(open(finalresultPath,'r'))[self.detectorName]
    except FileNotFoundError:
      print("File not found: " + str(finalresultPath))
      exit(1)

    

