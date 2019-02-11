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
    
class LocalResult(models.Model):
    ''' The result for a given sweep run for each dataset individually '''
    run = models.ForeignKey('Run',on_delete=models.CASCADE)
    dataset = models.ForeignKey('Dataset',on_delete=models.CASCADE)
    pred_error_no_anomaly = models.FloatField()
    pred_error_during_anomaly = models.FloatField()
    
class GlobalResult(models.Model):
    ''' The result for a given sweep for all datasets together '''
    run = models.ForeignKey('Run',on_delete=models.CASCADE)
    pred_error_no_anomaly = models.FloatField()
    pred_error_during_anomaly = models.FloatField()

