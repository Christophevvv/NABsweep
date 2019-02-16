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
    runs = Run.objects.all().filter(sweep__id = id)
    runvalues = RunValue.objects.all().filter(run__in=runs)\
                                      .order_by('sweep_parameter','value')

    grs = GlobalResultScore.objects.all().filter(global_result__run__in = runs)
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
    lr = LocalResult.objects.all().filter(run__id = id)
    gr = GlobalResult.objects.all().filter(run__id = id)
    assert(gr.count() == 1)
    gr = gr.get()
    gr.pred_error_no_anomaly = list(lr.aggregate(Sum('pred_error_no_anomaly')).values())[0]
    gr.pred_error_during_anomaly = list(lr.aggregate(Sum('pred_error_during_anomaly')).values())[0]
    local_scores = LocalResultScore.objects.all().filter(local_result__run__id = id)
    global_scores = GlobalResultScore.objects.all().filter(global_result=gr)
    for global_score in global_scores:
        #Add totals to this score since we did not store them explicitely
        ir = local_scores.filter(profile = global_score.profile)
        global_score.score = list(ir.aggregate(Sum('score')).values())[0]
        global_score.true_positives = list(ir.aggregate(Sum('true_positives')).values())[0]
        global_score.true_negatives = list(ir.aggregate(Sum('true_negatives')).values())[0]
        global_score.false_positives = list(ir.aggregate(Sum('false_positives')).values())[0]        
        global_score.false_negatives = list(ir.aggregate(Sum('false_negatives')).values())[0]
        
    #global_scores = global_scores.annotate(total_score=Value(3,output_field=IntegerField()))
    profiles = Profile.objects.all()
    context = {'run_id' : id, 'global_scores': global_scores,
               'local_scores': local_scores, 'profiles': profiles,
               'global_result': gr }

    return render(request,'results/run.html',context)
    
