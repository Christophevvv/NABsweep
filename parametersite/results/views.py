from django.shortcuts import render
from django.db.models import Sum,Count
from django.db.models import CharField, Value,IntegerField, FloatField
from django.views import generic
from .models import *

# Create your views here.

def index(request):
    ''' Show all sweep orders available '''
    sweep_orders = Sweep.objects.all().values('nr_params')\
                                .order_by('nr_params').distinct()
    context = {'sweep_order': sweep_orders }
    
    return render(request,'results/index.html',context)

def sweeps(request,order):
    ''' List all sweeps and their parameters for a given order '''
    result = {}
    sweeps = Sweep.objects.all().filter(nr_params = order)
    for sweep in sweeps:
        params = []
        sweep_params = SweepParameter.objects.all().filter(sweep = sweep)
        for sweep_param in sweep_params:
            params.append(sweep_param)
        result[sweep.id] = params
    sp = SweepParameter.objects.all().filter(sweep__nr_params = order)
    context = {'order': order, 'sweep_parameters': result}
    return render(request,'results/sweeps.html',context)

def sweep(request,id):
    ''' Show sweep with given id and list all of its runs'''
    #Return all runs of a given sweep
    runs = Run.objects.all().filter(sweep__id = id)
    #Queryset containing all parameter values for the runs of this sweep (sorted by parameter & val)
    runvalues = RunValue.objects.all().filter(run__in=runs)\
                                      .order_by('sweep_parameter','value')
    #All global results of all runs for this sweep:
    grs = GlobalResultScore.objects.all().filter(global_result__run__in = runs)
    #All defined profiles:
    profiles = Profile.objects.all()
    scores = {}
    for profile in profiles:
        grs_local = grs.filter(profile=profile)
        # grs_local.annotate(value='')
        # for grs_local_instance in grs_local:
        #     grs_local_instance.param_values = Value(RunValue.objects.all().filter(run = grs_local_instance.global_result.run).get(),output_field=FloatField())
        # grs_local = grs_local.order_by('param_values__value')
        # print(grs_local)

        # print(profile.name)
        #print(list(grs_local.values_list('normalized_score',flat=True)))
        #scores[profile.name] = [instance.normalized_score for instance in grs_local]
        results = []
        for runvalue in runvalues:
            print(runvalue)
            results.append(grs_local.filter(global_result__run = runvalue.run).get().normalized_score)
        scores[profile.name] = results
    value_list = list(runvalues.values_list('value',flat=True))
    score_list = []
    context = {'sweep_id': id, 'runs': runs, 'runvalues': runvalues,
               'x': value_list, 'y': scores, 'profiles': profiles}
    return render(request,'results/sweep.html',context)

def run(request,id):
    ''' Show run with given id and list all results (local + global) '''
    #All local results for this run (one per dataset)
    local_results = LocalResult.objects.all().filter(run__id = id)
    #The global result for this run
    global_result = GlobalResult.objects.all().filter(run__id = id)
    assert(global_result.count() == 1)
    #There can only be one global result per run. So we select this object:
    global_result = global_result.get()
    #Get all local result scores for this run (one per profile)
    local_scores = LocalResultScore.objects.all().filter(local_result__run__id = id)
    #Get all global result scores for this run (one per profile)
    global_scores = GlobalResultScore.objects.all().filter(global_result=global_result)
    
    #global_scores = global_scores.annotate(total_score=Value(3,output_field=IntegerField()))
    #global_scores, global_result, local_scores = _aggregateGlobal(id,True)
    #Baseline scores:
    #b_global_scores, b_global_result, b_local_scores = _aggregateGlobal(_getBaseLine().id)
    _addGlobalResultBaseline(global_result)
    _addGlobalScoresBaseline(global_scores)
    baseline_id = _getBaseline().id
    #Indicate whether this run is the original NAB parameter set
    original = (baseline_id == id)
    profiles = Profile.objects.all()
    context = {'run_id' : id, 'profiles': profiles, 'baseline_id': baseline_id,
               'original': original,
               'global_scores': global_scores,
               'local_scores': local_scores, 
               'global_result': global_result }
               # 'b_global_scores': b_global_scores,
               # 'b_global_result': b_global_result,
               # 'b_local_scores': b_local_scores }

    return render(request,'results/run.html',context)
    

def _addGlobalResultBaseline(global_result):
    ''' Add relative performance w.r.t baseline run to this global result '''
    #Get the baseline run:
    baseline = _getBaseline()
    #Get the global result for the baseline run:
    b_global_result = GlobalResult.objects.all().filter(run__id = baseline.id).get()
    #Add relative performance
    global_result.pred_error_no_anomaly_relative_baseline = ((float(global_result.pred_error_no_anomaly)/b_global_result.pred_error_no_anomaly)-1)*100
    global_result.pred_error_during_anomaly_relative_baseline = ((float(global_result.pred_error_during_anomaly)/b_global_result.pred_error_during_anomaly)-1)*100

def _addGlobalScoresBaseline(global_scores):
    ''' Add relative performance w.r.t baseline run to these global scores '''    
    #Get the baseline run:
    baseline = _getBaseline()
    #Get the global result for the baseline run:
    b_global_result = GlobalResult.objects.all().filter(run__id = baseline.id).get()    
    #Get all global result scores for baseline run (one per profile)
    b_global_scores = GlobalResultScore.objects.all().filter(global_result=b_global_result)
    #Add relative performance w.r.t baseline to each global score
    for global_score in global_scores:
        b_global_score = b_global_scores.filter(profile=global_score.profile).get()
        global_score.normalized_score_relative_baseline = ((float(global_score.normalized_score)/b_global_score.normalized_score)-1)*100
        global_score.score_relative_baseline = ((float(global_score.score)/b_global_score.score)-1)*100
        

def _addLocalBaseline():
    pass


# def _aggregateGlobal(run_id,add_baseline = False):
#     ''' Add aggregated local scores to global scores objects '''    
#     if add_baseline:
#         b_global_scores, b_gr, b_local_scores = _aggregateGlobal(_getBaseLine().id,False)
#     #All local results for this run (one per dataset)
#     lr = LocalResult.objects.all().filter(run__id = run_id)
#     #The global result for this run
#     gr = GlobalResult.objects.all().filter(run__id = run_id)
#     assert(gr.count() == 1)
#     #There can only be one global result per run. So we select this object:
#     gr = gr.get()
#     #Add prediction error score aggregates to global result:
#     gr.pred_error_no_anomaly = list(lr.aggregate(Sum('pred_error_no_anomaly')).values())[0]
#     gr.pred_error_during_anomaly = list(lr.aggregate(Sum('pred_error_during_anomaly')).values())[0]
#     if add_baseline:
#         gr.pred_error_no_anomaly_relative_baseline = ((float(gr.pred_error_no_anomaly)/b_gr.pred_error_no_anomaly)-1)*100
#         gr.pred_error_during_anomaly_relative_baseline = ((float(gr.pred_error_during_anomaly)/b_gr.pred_error_during_anomaly)-1)*100

#     #Get all local result scores for this run (one per profile)
#     local_scores = LocalResultScore.objects.all().filter(local_result__run__id = run_id)
#     #Get all global result scores for this run (one per profile)
#     global_scores = GlobalResultScore.objects.all().filter(global_result=gr)
#     #Add aggregated totals to the global scores (since we did not store them EXPLICITELY)
#     for global_score in global_scores:
#         #Intermediate Result: all local scores for this global score (=> for a given profile)
#         ir = local_scores.filter(profile = global_score.profile)
#         #Add aggregated results as new attributes:
#         global_score.score = list(ir.aggregate(Sum('score')).values())[0]
#         global_score.true_positives = list(ir.aggregate(Sum('true_positives')).values())[0]
#         global_score.true_negatives = list(ir.aggregate(Sum('true_negatives')).values())[0]
#         global_score.false_positives = list(ir.aggregate(Sum('false_positives')).values())[0]
#         global_score.false_negatives = list(ir.aggregate(Sum('false_negatives')).values())[0]
#         if add_baseline:
#             #b_ir = b_global_scores.filter(profile=global_score.profile)
#             for b_global_score in b_global_scores:
#                 if(b_global_score.profile == global_score.profile):
#                     global_score.score_relative_baseline = ((float(global_score.score)/b_global_score.score)-1)*100
#                     global_score.normalized_score_relative_baseline = ((float(global_score.normalized_score)/b_global_score.normalized_score)-1)*100
#                     break


#     #RETURNS:
#     # - 'global_scores' with aggregated scores,
#     # - 'gr': global result with aggregated prediction errors
#     # - local scores for completeness (nothing changed here,
#     #   but this may save us a redundant query in some cases where we also need the local scores)
#     return global_scores, gr, local_scores
    
def _getBaseline():
    ''' Returns the run where all parameters are standard NAB. Used as the baseline for results '''
    baseline = Run.objects.all().filter(sweep__nr_params = 0).get()
    return baseline
