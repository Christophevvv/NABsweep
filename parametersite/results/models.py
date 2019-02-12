from django.db import models

# Create your models here.
class Parameter(models.Model):
    group = models.CharField(max_length = 20)
    name = models.CharField(max_length = 30)

    class Meta:
        unique_together = (('group','name'),)

    def __str__(self):
        return str(self.group) + "_" + str(self.name)

class Category(models.Model):
    name = models.CharField(max_length = 50,unique=True)

    def __str__(self):
        return str(self.name)

class Dataset(models.Model):
    category = models.ForeignKey('Category',on_delete=models.CASCADE)
    name = models.CharField(max_length = 50)
    length = models.IntegerField()

    class Meta:
        unique_together = (('category','name'),)

    def __str__(self):
        return str(self.category) + "/" + str(self.name)

class Sweep(models.Model):
    ''' A sweep instance '''
    nr_params = models.IntegerField()

    def __str__(self):
        return "Sweep " + str(self.id) + " with " + str(self.nr_params) + " parameters."

class SweepParameter(models.Model):
    ''' The parameters this sweep is using '''
    sweep = models.ForeignKey('Sweep',on_delete=models.CASCADE)
    parameter = models.ForeignKey('Parameter',on_delete=models.CASCADE)

    class Meta:
        unique_together = (('sweep','parameter'),)

    def __str__(self):
        return str(self.parameter) + " - " + str(self.sweep)

class Run(models.Model):
    ''' A run of a given sweep '''
    #description = models.CharField(max_length = 128)
    sweep = models.ForeignKey('Sweep',on_delete=models.CASCADE)

    def __str__(self):
        return "Run " + str(self.id) + " for " + str(self.sweep)
    
class RunValue(models.Model):
    ''' All the values for each parameter for a given run '''
    run = models.ForeignKey('Run',on_delete=models.CASCADE)
    sweep_parameter = models.ForeignKey('SweepParameter',on_delete=models.CASCADE)
    #parameter = models.ForeignKey('Parameter',on_delete=models.CASCADE)
    value = models.FloatField()

    class Meta:
        unique_together = (('run','sweep_parameter','value'),)
        #Add constraint to link parameter with run.sweep -> sweepparameter?

    def __str__(self):
        return "Value of " + str(self.value) + " for " + str(self.run) + " with " + str(self.sweep_parameter)

class Profile(models.Model):
    name = models.CharField(max_length = 250,unique=True)
    tp_weight = models.FloatField()
    fp_weight = models.FloatField()
    tn_weight = models.FloatField()
    fn_weight = models.FloatField()

    def __str__(self):
        return "Profile: " + str(self.name)
    
class LocalResult(models.Model):
    ''' The result for a given sweep run for each dataset individually '''
    run = models.ForeignKey('Run',on_delete=models.CASCADE)
    dataset = models.ForeignKey('Dataset',on_delete=models.CASCADE)
    pred_error_no_anomaly = models.FloatField()
    pred_error_during_anomaly = models.FloatField()

    class Meta:
        unique_together = (('run','dataset'),)

    def __str__(self):
        return "Local Result for " + str(self.dataset)

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

    def __str__(self):
        return "Score of " + str(self.local_result) + " for " + str(self.profile)
    
class GlobalResult(models.Model):
    ''' The result for a given sweep for all datasets together '''
    run = models.OneToOneField('Run',on_delete=models.CASCADE)

    def __str__(self):
        return "Global result for " + str(self.run)

class GlobalResultScore(models.Model):
    #You can aggregate localresult scores to get total score/tp/tn/fp/fn...
    global_result = models.ForeignKey('GlobalResult',on_delete=models.CASCADE)
    profile = models.ForeignKey('Profile',on_delete=models.CASCADE)
    threshold = models.FloatField()
    normalized_score = models.FloatField() #0-100

    class Meta:
        unique_together = (('global_result','profile'),)

    def __str__(self):
        return "Score of " + str(self.global_result) + " for " + str(self.profile)
