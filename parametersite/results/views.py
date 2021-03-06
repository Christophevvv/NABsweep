from django.shortcuts import render
from django.db.models import Sum,Count,Avg
from django.db.models import CharField, Value,IntegerField, FloatField
from django.db.models.functions import Cast
from django.views import generic
from .models import *
import numpy as np

# Create your views here.

def index(request):
    ''' Show all sweep orders available '''
    sweep_orders = Sweep.objects.all().values('nr_params')\
                                .order_by('nr_params').distinct()
    context = {'sweep_order': sweep_orders }
    
    return render(request,'results/index.html',context)

def dashboard(request):
    profiles = Profile.objects.all()
    scores = {}
    for profile in profiles:
        global_scores = GlobalResultScore.objects.all()\
                                                 .filter(profile=profile)\
                                                 .order_by('normalized_score')
        for global_score in global_scores:
            _addGlobalResultBaseline(global_score.global_result)
        _addGlobalScoresBaseline(global_scores)
        scores[profile.name] = global_scores
    context = { 'scores': scores }
    return render(request,'results/dashboard.html',context)

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
    sweep = Sweep.objects.all().filter(id=id).get()
    nr_params = sweep.nr_params
    #Return all runs of a given sweep
    runs = Run.objects.all().filter(sweep__id = id)
    #Queryset containing all parameter values for the runs of this sweep (sorted by parameter & val)
    runvalues = RunValue.objects.all().filter(run__in=runs)#.order_by('sweep_parameter','value')
    #FIX for ordering on value
    runvalues = runvalues.annotate(value_as_float=Cast('value',FloatField())).order_by('sweep_parameter','value_as_float')
    renderGraphs = False
    if nr_params == 1:
        renderGraphs = True
        runs = []
        for runvalue in runvalues:
            runs.append(runvalue.run)
        
    #======NEW PART==========
    #assume only one runvalue per run (otherwise we can't make 2d plot)
    profiles = Profile.objects.all()
    scores = {}
    #TO DELETE
    prediction_errors = {}
    baseline_scores = {}
    baseline_prediction_errors = {}
    #TO DELETE END --
    for profile in profiles:
        scores[profile.name] = { 'normalized_scores': [],
                                 'normalized_scores_std': [],
                                 'prediction_errors': [],
                                 'prediction_errors_std': [],
                                 'baseline_scores': [],
                                 'baseline_prediction_errors': []
                                 }
    for run in runs:
        aggregated_run = _aggregateRun(run)
        for profile in profiles:
            scores[profile.name]['normalized_scores'].append(np.mean(aggregated_run[profile.name]['normalized_scores']))
            scores[profile.name]['normalized_scores_std'].append(np.std(aggregated_run[profile.name]['normalized_scores']))
            scores[profile.name]['prediction_errors'].append(np.mean(aggregated_run[profile.name]['pred_error_no_anomaly']))
            scores[profile.name]['prediction_errors_std'].append(np.std(aggregated_run[profile.name]['pred_error_no_anomaly']))
            if profile.name == "standard":
                run.normalized_score = round(scores[profile.name]['normalized_scores'][-1],2)
                run.std = round(scores[profile.name]['normalized_scores_std'][-1],2)
            elif profile.name == "reward_low_FP_rate":
                run.normalized_score_low_FP = round(scores[profile.name]['normalized_scores'][-1],2)
                run.std_low_FP = round(scores[profile.name]['normalized_scores_std'][-1],2)
            elif profile.name == "reward_low_FN_rate":
                run.normalized_score_low_FN = round(scores[profile.name]['normalized_scores'][-1],2)
                run.std_low_FN = round(scores[profile.name]['normalized_scores_std'][-1],2)
                

    baseline_aggregated_run = _aggregateRun(_getBaseline())
    baselines = {}
    for profile in profiles:
        mean = np.mean(baseline_aggregated_run[profile.name]['normalized_scores'])
        std = np.std(baseline_aggregated_run[profile.name]['normalized_scores'])
        baselines[profile.name] = { 'mean': round(mean,2), 'std': round(std,2)}
        scores[profile.name]['baseline_scores'] = [mean]*len(scores[profile.name]['normalized_scores'])
        scores[profile.name]['baseline_prediction_errors'] = [np.mean(baseline_aggregated_run[profile.name]['pred_error_no_anomaly'])]*len(scores[profile.name]['prediction_errors'])

    for run in runs:
        run.std_baseline = ((run.normalized_score/float(baselines["standard"]["mean"]))-1)*100
        run.low_fp_baseline = ((run.normalized_score_low_FP/float(baselines["reward_low_FP_rate"]["mean"]))-1)*100
        run.low_fn_baseline = ((run.normalized_score_low_FN/float(baselines["reward_low_FN_rate"]["mean"]))-1)*100


    #========================
    # #All global results of all runs for this sweep:
    # grs = GlobalResultScore.objects.all().filter(global_result__run__in = runs)
    # #All defined profiles:
    # profiles = Profile.objects.all()
    # scores = {}
    # prediction_errors = {}
    # baseline_scores = {}
    # baseline_prediction_errors = {}
    # for profile in profiles:
    #     grs_local = grs.filter(profile=profile)
    #     # grs_local.annotate(value='')
    #     # for grs_local_instance in grs_local:
    #     #     grs_local_instance.param_values = Value(RunValue.objects.all().filter(run = grs_local_instance.global_result.run).get(),output_field=FloatField())
    #     # grs_local = grs_local.order_by('param_values__value')
    #     # print(grs_local)

    #     # print(profile.name)
    #     #print(list(grs_local.values_list('normalized_score',flat=True)))
    #     #scores[profile.name] = [instance.normalized_score for instance in grs_local]
    #     result_scores = []
    #     result_prediction_error = []
    #     for runvalue in runvalues:
    #         #print(runvalue)
    #         result_scores.append(grs_local.filter(global_result__run = runvalue.run).get().normalized_score)
    #         result_prediction_error.append(grs_local.filter(global_result__run = runvalue.run).get().global_result.pred_error_no_anomaly)
            
    #     scores[profile.name] = result_scores
    #     prediction_errors[profile.name] = result_prediction_error
    #     baseline_scores[profile.name] = [GlobalResultScore.objects.all().filter(global_result__run = _getBaseline(),profile=profile).get().normalized_score]*len(result_scores)
    #     baseline_prediction_errors[profile.name] = [GlobalResultScore.objects.all().filter(global_result__run = _getBaseline(),profile=profile).get().global_result.pred_error_no_anomaly]*len(result_prediction_error)
    #value_list = list(runvalues.values_list('value',flat=True))
    value_list = []
    try:
        value_list = [float(x) if not (x[0] == '[') else float(list(x[1:-1].split(','))[1]) for x in list(runvalues.values_list('value',flat=True))]
    except:
        value_list = list(runvalues.values_list('value',flat=True))
        renderGraph = False
        
    score_list = []
    context = {'sweep_id': id, 'runs': runs, 'runvalues': runvalues,
               'x': value_list, 'scores': scores, 'profiles': profiles,
               'renderGraphs': renderGraphs, 'baselines': baselines}
               # 'baseline_scores': baseline_scores,
               # 'prediction_errors': prediction_errors,
               # 'baseline_prediction_errors': baseline_prediction_errors}
    return render(request,'results/sweep.html',context)

def _aggregateRun(run):
    ''' This function returns a dictionary for the given run, with an entry for each profile.
    Each profile contains the normalized score among all seed combinations as well as the normal
    score, tp,tn,fp and fn. '''
    #Return all global results for run (with possibly different seeds)
    global_results = GlobalResult.objects.all().filter(run = run)
    profiles = Profile.objects.all()
    result = {}
    for profile in profiles:
        normalized_scores = []
        scores = []
        pred_error_no_anomaly = []
        pred_error_during_anomaly = []
        tp = []
        tn = []
        fp = []
        fn = []
        for global_result in global_results:
            global_result_score = GlobalResultScore.objects.all().filter(global_result=global_result,
                                                                         profile=profile).get() #unique        
            normalized_scores.append(global_result_score.normalized_score)
            scores.append(global_result_score.score)
            pred_error_no_anomaly.append(global_result.pred_error_no_anomaly)
            pred_error_during_anomaly.append(global_result.pred_error_during_anomaly)
            tp.append(global_result_score.true_positives)
            tn.append(global_result_score.true_negatives)
            fp.append(global_result_score.false_positives)
            fn.append(global_result_score.false_negatives)
        
        result[profile.name] = { 'normalized_scores': normalized_scores,
                                 'scores': scores,
                                 'pred_error_no_anomaly': pred_error_no_anomaly,
                                 'pred_error_during_anomaly': pred_error_during_anomaly,
                                 'true_positives': tp,
                                 'true_negatives': tn,
                                 'false_positives': fp,
                                 'false_negatives': fn
                                 }
    return result

def run(request,id):
    ''' Show run with given id and list all results (local + global) '''
    #All local results for this run (one per dataset)
    local_results = LocalResult.objects.all().filter(run__id = id)
    #The global result for this run
    global_results = GlobalResult.objects.all().filter(run__id = id)
    avg_global_result = GlobalResult(run = global_results[0].run,
                                     seeds = global_results[0].seeds,
                                     pred_error_no_anomaly = global_results.aggregate(Avg('pred_error_no_anomaly'))['pred_error_no_anomaly__avg'],
                                     pred_error_during_anomaly = global_results.aggregate(Avg('pred_error_during_anomaly'))['pred_error_during_anomaly__avg'])

    #assert(global_result.count() == 1)
    #There can only be one global result per run. So we select this object:
    #global_result = global_result.get()
    #Get all local result scores for this run (one per profile)
    local_scores = LocalResultScore.objects.all().filter(local_result__run__id = id)
    #Get all global result scores for this run (one per profile)
    global_scores = GlobalResultScore.objects.all().filter(global_result__in=global_results)
    
    #global_scores = global_scores.annotate(total_score=Value(3,output_field=IntegerField()))
    #global_scores, global_result, local_scores = _aggregateGlobal(id,True)
    #Baseline scores:
    #b_global_scores, b_global_result, b_local_scores = _aggregateGlobal(_getBaseLine().id)
    #_addGlobalResultBaseline(global_result)
    #_addGlobalScoresBaseline(global_scores)
    baseline_id = _getBaseline().id
    #Indicate whether this run is the original NAB parameter set
    original = (baseline_id == id)
    profiles = Profile.objects.all()

    avg_dataset_scores = {}
    for profile in profiles:
        categories = {}
        for category in Category.objects.all():
            #all local results for datasets in given category:
            lr_dataset = local_results.filter(dataset__category = category)
            lrs_p = LocalResultScore.objects.all().filter(profile=profile,local_result__in=lr_dataset)
            avg_score = lrs_p.aggregate(Avg('score'))['score__avg']
            categories[category.name] = avg_score
        avg_dataset_scores[profile.name]=categories
            
    
    runvalues = RunValue.objects.all().filter(run__id = id).order_by('sweep_parameter__parameter__group')
    context = {'run_id' : id, 'profiles': profiles, 'baseline_id': baseline_id,
               'original': original,
               'global_scores': global_scores,
               'local_scores': local_scores, 
               'global_result': avg_global_result,#global_result,
               'dataset_scores': avg_dataset_scores,
               'runvalues': runvalues}
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
        global_score.score_relative_baseline = global_score.score - b_global_score.score
        

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
