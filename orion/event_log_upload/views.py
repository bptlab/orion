from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.template.defaulttags import register
import os
import pandas as pd
from orion.CPA import CPA
from orion.variants.variant_comparator import VariantComparator
from orion.plotting import plot_cell_correlation
import pm4py
from . import change_pattern_matrix
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
from pm4py.visualization.dfg import visualizer as dfg_visualization
from pm4py.statistics.eventually_follows.log import get as efg_get
from pm4py.algo.filtering.dfg import dfg_filtering
import pygraphviz as pgv
from django.contrib.auth.decorators import login_required

@register.filter

def get_item(dictionary, key):
    return dictionary.get(key)
# Create your views here.


dynamic_event_attribute_label = "Dynamic Event Attributes have not been detected yet"
context_aware_label = "Context-Awareness has not been applied yet"
dynamic_event_attribute_button_enabled = True
context_aware_button_enabled = True
context = {}

@login_required
def index(request):
    return render(request, "event_log_upload.html")

def generate_process_model(act_filter = 1, path_filter = 0.2, att_config={}):
    global analyzer
    dfg, sa, ea = pm4py.discover_directly_follows_graph(analyzer.event_log)
    activities_count = pm4py.get_event_attribute_values(analyzer.event_log, "concept:name")
    dfg, sa, ea, activities_count = dfg_filtering.filter_dfg_on_activities_percentage(dfg, sa, ea, activities_count, act_filter)
    dfg, sa, ea, activities_count = dfg_filtering.filter_dfg_on_paths_percentage(dfg, sa, ea, activities_count, path_filter)
    param={}
    param["START_ACTIVITIES"] = sa
    param["END_ACTIVITIES"] = ea
    dfg_image = dfg_visualization.apply(dfg, att_config=att_config, log=analyzer.event_log, variant=dfg_visualization.Variants.FREQUENCY, parameters = param)
    dfg_image_py = pgv.AGraph()
    dfg_image_py.read(dfg_image.save())
    dfg_path = os.path.join(settings.MEDIA_ROOT, "process_model.png")
    dfg_image_py.draw(dfg_path, prog="dot")
    analyzer.dfg = dfg
    efg = efg_get.apply(analyzer.event_log)
    act_list = list(activities_count.keys())
    filter_df = pd.DataFrame(columns=["Act_Filter", "Path_Filter"])
    row = {"Act_Filter":act_filter, "Path_Filter":path_filter}
    filter_df = filter_df.append(row, ignore_index=True)
    filter_df.to_csv(os.path.join(settings.MEDIA_ROOT, "filter_df.csv"))

    rel_to_delete = []
    for rel in efg:
        if (rel[0] not in act_list) or (rel[1] not in act_list):
            rel_to_delete.append(rel)
    for rel in rel_to_delete:
        efg.pop(rel, None)
    analyzer.efg = efg

@login_required
def update_pm_slider(request):
    global context
    global analyzer
    if request.method == "POST":
        act_threshold = request.POST["act_threshold_slider"]
        path_threshold = request.POST["path_threshold_slider"]
        generate_process_model(float(act_threshold), float(path_threshold))
        context["act_slider_value"] = act_threshold
        context["path_slider_value"] = path_threshold
    return render(request, "main.html", context)

@login_required
def upload_page(request):
    log_path = os.path.join(settings.MEDIA_ROOT, "event_logs")

    if request.method == "POST":
        if "uploadButton" in request.POST:
            global context
            
            log = request.FILES["event_log"]
            fs = FileSystemStorage(log_path)
            filename = fs.save(log.name, log)
            file_dir = os.path.join(log_path, filename)
            context = {}
            context["file_dir"] = file_dir
            csv_log = pd.read_csv(context["file_dir"])
            context["columns"] = list(csv_log.columns)
            return render(request, "mandatory_attribute_selection.html", context)

@login_required       
def set_mandatory_attributes(request):
    global context
    global analyzer
    global dynamic_event_attribute_label
    global context_aware_label
    global dynamic_event_attribute_button_enabled
    global context_aware_button_enabled
    csv_log = pd.read_csv(context["file_dir"])
    if request.method == "POST":
        selected_case = request.POST.get('case_dropdown')
        selected_act = request.POST.get('activity_dropdown')
        selected_time = request.POST.get('timestamp_dropdown')
        columns_to_drop = request.POST.getlist('columns_to_drop')
        analyzer = CPA(csv_log, selected_case, selected_act, selected_time, columns_to_drop)
        analyzer.add_variants()
        generate_process_model()
        file_path = os.path.join(settings.MEDIA_ROOT, "event_log.xes")
        pm4py.write_xes(analyzer.event_log, file_path)
        dynamic_event_attribute_label = "Dynamic Event Attributes have not been detected yet"
        context_aware_label = "Context-Awareness has not been applied yet"
        context["dynamic_event_attribute_label"] = dynamic_event_attribute_label
        context["context_aware_label"] = context_aware_label
        context["dynamic_event_attribute_button_enabled"] = dynamic_event_attribute_button_enabled
        context["context_aware_button_enabled"] = context_aware_button_enabled
        context["act_slider_value"] = 1
        context["path_slider_value"] = 0.2
    return render(request, "main.html", context)

@login_required
def detect_dynamic_event_attributes(request):
    global dynamic_event_attribute_label
    global analyzer
    global context
    dynamic_event_attribute_label = "Dynamic Event Attributes detected"
    context["dynamic_event_attribute_label"] = dynamic_event_attribute_label
    context["context_aware_label"] = context_aware_label
    analyzer.prepare_attribute_classification()
    dynamic_list = analyzer.classification_scores_con_cat.copy()
    dynamic_list = dynamic_list.loc[dynamic_list["class"] == "dynamic"]
    dynamic_list = list(dynamic_list.index)
    context["dynamic_list"] = dynamic_list
    context["slider_value"] = "0.05"
    context["show_con_cat"] = False


    return render(request, "dynamic_attribute_detection.html", context)

@login_required
def classify_data_type(request):
    global analyzer
    global context
    if request.method == "POST" and "con_cat_slider_value" in request.POST:
        att_class_threshold = request.POST["con_cat_slider_value"]
        analyzer.classify_attribute_type(float(att_class_threshold))
        analyzer.compute_con_cat_attribute_list()
        context["attribute_list_con"] = analyzer.attribute_list_con
        context["attribute_list_cat"] = analyzer.attribute_list_cat
        context["slider_value"] = att_class_threshold
        context["show_con_cat"] = True

    return render(request, "dynamic_attribute_detection.html", context)

@login_required
def switch_data_type(request):
    global context
    global analyzer
    if request.method == "POST":
        remove_con = request.POST.getlist('con_list')
        remove_cat = request.POST.getlist('cat_list')
        con_list = context["attribute_list_con"]
        cat_list = context["attribute_list_cat"]
        for con in remove_con:
            con_list.remove(con)
            cat_list.append(con)
        for cat in remove_cat:
            cat_list.remove(cat)
            con_list.append(cat)
        context["attribute_list_con"] = con_list
        context["attribute_list_cat"] = cat_list
        analyzer.attribute_list_con = con_list
        analyzer.attribute_list_cat = cat_list
    
    return render(request, "dynamic_attribute_detection.html", context)

@login_required
def conclude_dynamic_attribute_detection(request):
    global analyzer
    global context
    global dynamic_event_attribute_button_enabled
    dynamic_event_attribute_button_enabled = False
    context["dynamic_event_attribute_button_enabled"] = dynamic_event_attribute_button_enabled
    return render(request, "main.html", context)


################DYNAMIC ATTRIBUTE + DATA TYPE DETECTION FINISHED###################
@login_required
def detect_context_aware_activities(request):
    global context_aware_label
    global analyzer
    global context
    rep_scores = analyzer.repetition_scores.copy()
    rep_scores = rep_scores.reset_index()
    rep_scores["repetition_score"] = rep_scores["repetition_score"].astype("float")
    rep_scores["repetition_score"] = rep_scores["repetition_score"].round(4)
    rep_scores["repetition_score"] = rep_scores["repetition_score"].astype("string")
    rep_scores["act_rep_score"] = rep_scores["index"] + ": " + rep_scores["repetition_score"]
    context["activity_list"] = rep_scores["act_rep_score"]
    context["show_context_identification"] = False
    context_aware_label = "Context-Aware activities detcted"
    context["dynamic_event_attribute_label"] = dynamic_event_attribute_label
    context["context_aware_label"] = context_aware_label


    return render(request, "context_aware.html", context)

@login_required
def set_recurring_activity(request):
    global context
    global analyzer
    if request.method == "POST":
        rec_acts = request.POST.getlist('activity_list')
        rec_acts = [rec_act.split(":")[0] for rec_act in rec_acts]
        context["rec_acts"] = rec_acts
        context["slider_value"] = 0.5
        context["show_context_identification"] = True
        analyzer.set_recurring_activities(rec_acts)
        analyzer.identify_context(context["slider_value"], [])
        context["mapping_before"] = analyzer.mapping_before
        context["mapping_after"] = analyzer.mapping_after
    return render(request, "context_aware.html", context)

@login_required
def update_context_slider(request):
    global context
    global analyzer
    if request.method == "POST":
        context_threshold = request.POST["context_threshold_slider"]
        analyzer.identify_context(float(context_threshold), [])
        context["mapping_before"] = analyzer.mapping_before
        context["mapping_after"] = analyzer.mapping_after
        context["slider_value"] = context_threshold
    return render(request, "context_aware.html", context)

@login_required
def remove_context_from_activity(request):
    global context
    global analyzer
    for rec_act in context["rec_acts"]:
        map_before = request.POST.getlist("mapping_before_list_" + rec_act)
        map_after = request.POST.getlist("mapping_after_list_" + rec_act)
        for act_to_remove in map_before:
            index_to_remove = analyzer.mapping_before[rec_act].index(act_to_remove)
            del analyzer.mapping_before[rec_act][index_to_remove]
        for act_to_remove in map_after:
            index_to_remove = analyzer.mapping_after[rec_act].index(act_to_remove)
            del analyzer.mapping_after[rec_act][index_to_remove]
        
    context["mapping_before"] = analyzer.mapping_before
    context["mapping_after"] = analyzer.mapping_after

    return render(request, "context_aware.html", context)

@login_required
def conclude_context_aware_activities(request):
    global analyzer
    global context
    global context_aware_button_enabled
    analyzer.transform_event_log()
    analyzer.add_variants()
    analyzer.prepare_attribute_classification()
    context_aware_button_enabled = False
    context["context_aware_button_enabled"] = context_aware_button_enabled
    generate_process_model()
    file_path = os.path.join(settings.MEDIA_ROOT, "event_log.xes")
    pm4py.write_xes(analyzer.event_log, file_path)
    
    return render(request, "main.html", context)

############################CONTEXT-AWARENESS FINISHED#########################

@login_required
def detect_change_patterns(request):
    global analyzer
    global context
    analyzer.initialize_change_pattern_detection()
    analyzer.detect_continuous_change_patterns_dfg()
    analyzer.detect_continuous_change_patterns_efg()
    analyzer.detect_categorical_change_patterns_dfg()
    analyzer.detect_categorical_change_patterns_efg()
    analyzer.perform_fdr_correction()
    file_path = os.path.join(settings.MEDIA_ROOT, "change_patterns.csv")
    analyzer.change_patterns_corrected.to_csv(file_path)
    return render(request, "main.html", context)

@login_required
def explore_change_patterns(request):
    global context
    global analyzer
    context["show_change_patterns"] = True
    return render(request, "main.html", context)


############################CHANGE DETECTION FINISHED#########################

@login_required
def detect_relationships(request):
    global context
    global analyzer
    analyzer.initialize_relationship_detection()
    analyzer.prepare_correlation()
    analyzer.compute_correlation()
    analyzer.correlation_df_corrected.to_csv(os.path.join(settings.MEDIA_ROOT, "correlation_df.csv"))
    

    return render(request, "main.html", context)