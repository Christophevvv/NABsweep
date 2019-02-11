from django.db import models

# Create your models here.
class Parameter(models.Model):
    group = models.CharField(max_length = 20)
    name = models.CharField(max_length = 30)

    class Meta:
        unique_together = (('group','name'),)

class Category(models.Model):
    name = models.CharField(max_length = 50,unique=True)

class Dataset(models.Model):
    category = models.ForeignKey('Category',on_delete=models.CASCADE)
    name = models.CharField(max_length = 50)
    length = models.IntegerField()

    class Meta:
        unique_together = (('category','name'),)

class Sweep(models.Model):
    ''' A sweep instance '''
    nr_params = models.IntegerField()

class SweepParameter(models.Model):
    ''' The parameters this sweep is using '''
    sweep = models.ForeignKey('Sweep',on_delete=models.CASCADE)
    parameter = models.ForeignKey('Parameter',on_delete=models.CASCADE)

    class Meta:
        unique_together = (('sweep','parameter'),)    

class Run(models.Model):
    ''' A run of a given sweep '''
    #description = models.CharField(max_length = 128)
    sweep = models.ForeignKey('Sweep',on_delete=models.CASCADE)
    
class RunValue(models.Model):
    ''' All the values for each parameter for a given run '''
    run = models.ForeignKey('Run',on_delete=models.CASCADE)
    sweep_parameter = models.ForeignKey('SweepParameter',on_delete=models.CASCADE)
    #parameter = models.ForeignKey('Parameter',on_delete=models.CASCADE)
    value = models.FloatField()

    class Meta:
        unique_together = (('run','sweep_parameter','value'),)
        #Add constraint to link parameter with run.sweep -> sweepparameter?

class Profile(models.Model):
    name = models.CharField(max_length = 256,unique=True)
    tp_weight = models.FloatField()
    fp_weight = models.FloatField()
    tn_weight = models.FloatField()
    fn_weight = models.FloatField()
    
class LocalResult(models.Model):
    ''' The result for a given sweep run for each dataset individually '''
    run = models.ForeignKey('Run',on_delete=models.CASCADE)
    dataset = models.ForeignKey('Dataset',on_delete=models.CASCADE)
    pred_error_no_anomaly = models.FloatField()
    pred_error_during_anomaly = models.FloatField()

    class Meta:
        unique_together = (('run','dataset'),)    

class LocalResultScore(models.Model):
    local_result = models.ForeignKey('LocalResult',on_delete=models.CASCADE)
    profile = models.ForeignKey('Profile',on_delete=models.CASCADE)
    score = models.FloatField()
    true_positives = models.IntegerField()
    true_negatives = models.IntegerField()
    false_positives = models.IntegerField()
    false_negatives = models.IntegerField()

    class Meta:
        unique_together = (('local_result','profile'),)        
    
class GlobalResult(models.Model):
    ''' The result for a given sweep for all datasets together '''
    run = models.ForeignKey('Run',on_delete=models.CASCADE)

class GlobalResultScore(models.Model):
    #You can aggregate localresult scores to get total score/tp/tn/fp/fn...
    global_result = models.ForeignKey('GlobalResult',on_delete=models.CASCADE)
    profile = models.ForeignKey('Profile',on_delete=models.CASCADE)
    threshold = models.FloatField()
    normalized_score = models.FloatField() #0-100

    class Meta:
        unique_together = (('global_result','profile'),)
