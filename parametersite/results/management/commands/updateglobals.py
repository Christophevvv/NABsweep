from django.core.management.base import BaseCommand
from django.db import transaction
from results.models import *
from django.db.models import Sum

class Command(BaseCommand):
    def handle(self, *args, **options):
        self.update()

    def update(self):
        print("updating globals")
        runs = Run.objects.all()
        for run in runs:
            self.updateRun(run.id)

    @transaction.atomic
    def updateRun(self,run_id):
        ''' Aggregate local results and add them to global results '''
        #All local results for this run (one per dataset)
        lr = LocalResult.objects.all().filter(run__id = run_id)
        #The global result for this run
        gr = GlobalResult.objects.all().filter(run__id = run_id)
        assert(gr.count() == 1)
        #There can only be one global result per run. So we select this object:
        gr = gr.get()
        #Add prediction error score aggregates to global result:
        gr.pred_error_no_anomaly = list(lr.aggregate(Sum('pred_error_no_anomaly')).values())[0]
        gr.pred_error_during_anomaly = list(lr.aggregate(Sum('pred_error_during_anomaly')).values())[0]
        gr.save()
        #Get all local result scores for this run (one per profile)
        local_scores = LocalResultScore.objects.all().filter(local_result__run__id = run_id)
        #Get all global result scores for this run (one per profile)
        global_scores = GlobalResultScore.objects.all().filter(global_result=gr)
        #Add aggregated totals to the global scores (since we did not store them EXPLICITELY)
        for global_score in global_scores:
            #Intermediate Result: all local scores for this global score (=> for a given profile)
            ir = local_scores.filter(profile = global_score.profile)
            #Add aggregated results as new attributes:
            global_score.score = list(ir.aggregate(Sum('score')).values())[0]
            global_score.true_positives = list(ir.aggregate(Sum('true_positives')).values())[0]
            global_score.true_negatives = list(ir.aggregate(Sum('true_negatives')).values())[0]
            global_score.false_positives = list(ir.aggregate(Sum('false_positives')).values())[0]
            global_score.false_negatives = list(ir.aggregate(Sum('false_negatives')).values())[0]
            global_score.save()                        
