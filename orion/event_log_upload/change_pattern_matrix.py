import dash_bootstrap_components as dbc
import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
from dash import dash_table
import plotly.graph_objects as go
import dash_mantine_components as dmc
import plotly.express as px
import pandas as pd
import json
from django_plotly_dash import DjangoDash
from django.conf import settings
import os
import numpy as np
import pm4py
from pm4py.visualization.dfg import visualizer as dfg_visualization
from pm4py.algo.filtering.dfg import dfg_filtering
from django.conf import settings
import pygraphviz as pgv

def fill_heatmap_data(x_axis, y_axis, z_axis, x_val, y_val, z_val, df, effect_size):
    df_2_d = df.loc[df[z_axis] == z_val] 
    data = []
    annotation = []
    for y in y_val:
        buff = np.empty(len(x_val), dtype=object)
        buff_anno = np.empty(len(x_val), dtype=object)
        for i in range(0, len(x_val)):
            x = x_val[i]
            try:
                row = df_2_d.loc[(df_2_d[x_axis] == x) & (df_2_d[y_axis] == y)].iloc[0]
                buff[i] = row[effect_size]
                #change depending on data type
                if data_type == "Continuous":
                    p = str(row["P"])
                    m1 = str(row["M1"].round(2))
                    m2 = str(row["M2"].round(2))
                    sample_size = str(row["#Samples"])
                    buff_anno[i] = "Change in mean values: "  + m1 + "<span>&#8594;</span>" + m2 + "<br>P: " + p + "<br>Samples: " + sample_size  
                else:
                    p = str(row["P"])
                    sample_size = str(row["#Samples"])
                    buff_anno[i] = "P: " + p + "<br>Samples: " + sample_size  
            except:
                buff[i] = 0
                buff_anno[i] = "No information available"
        data.append(buff.tolist())
        annotation.append(buff_anno.tolist())
    return data, annotation

def create_figure_con(x_val, y_val, data, annotation, x_title, y_title):
    return {
            'data': [go.Heatmap(
            x=x_val,
            y=y_val,
            z=data,
            hovertext = annotation,
            texttemplate="%{text}",
            reversescale=True,
            colorscale='RdBu',
            zmin=-1, zmax=1, zmid=0, text = np.round(data, 2)),
            ],
            'layout': go.Layout(
            xaxis = dict(title = x_title, tickfont = dict(size = 12)),
            yaxis = dict(title = y_title, tickfont = dict(size = 10)),
            margin = dict(l=200),
            )}

def create_figure_cat(x_val, y_val, data, annotation, x_title, y_title):
    return {
            'data': [go.Heatmap(
            x=x_val,
            y=y_val,
            z=data,
            hovertext = annotation,
            texttemplate="%{text}",
            colorscale='bluered',
            zmin=0, text = np.round(data, 2)),
            ],
            'layout': go.Layout(
            xaxis = dict(title = x_title, tickfont = dict(size = 12)),
            yaxis = dict(title = y_title, tickfont = dict(size = 10)),
            margin = dict(l=200),
            )}

def prepare_value_list(x):
    global data_type
    x = x.replace("[", "")
    x = x.replace("]", "")
    if data_type == "Categorical":
        x = x.replace("'", "")
    y = x.split(", ")
    if data_type == "Continuous":
        y = [float(i) for i in y]
    return y

def prepare_value_list_rel(x, x_dtype):
    x = x.replace("[", "")
    x = x.replace("]", "")
    x = x.replace("\n", "")
    
    if x_dtype == "Categorical":
        x = x.replace("...", "")
        x = x.replace("  ", " ")
        y = x.split("' '")
        y[0] = y[0].replace("'", "")
        y[len(y)-1] = y[len(y)-1].replace("'", "")
    else:
        x = x.replace("...", "")
        y = x.split(" ")
    y = [x for x in y if len(x)>0]
    if x_dtype == "Continuous":
        y = [float(i) for i in y]
    return y


def plot_cell_correlation(row):
    values_1 = row["values_1"]
    values_2 = row["values_2"]
    if row["method"] == "pearson" or row["method"] == "spearman":
        values_1 = prepare_value_list_rel(values_1, "Continuous")
        values_2 = prepare_value_list_rel(values_2, "Continuous")
    
        title = f"{row['Activity 1']} -> {row['Activity 2']}: {row['R'].round(2)}"
        xlabel = "Δ" + row["measure_1"]
        ylabel = "Δ" + row["measure_2"]

        fig_rel = {
            'data': [
                go.Scatter(
                mode="markers",
                x=values_1,
                y=values_2,
                marker=dict(color='red'),
                name="Change Pattern Value Differences")],
            'layout': go.Layout(
                xaxis = dict(title = xlabel),
                yaxis = dict(title = ylabel),
                )
        } 
    elif row["method"] == "cramer":
        values_1 = prepare_value_list_rel(values_1, "Categorical")
        values_2 = prepare_value_list_rel(values_2, "Categorical")
        df_cross = pd.crosstab(index=values_1, columns=values_2)
        data = []
        for x in df_cross.columns:
            data.append(go.Bar(name=str(x), x=df_cross.index, y=df_cross[x]))
        fig_rel = {
            'data': data,
            'layout': go.Layout(
                barmode = "group"
                )
        }
    elif row["method"] == "kruskal":
        #BOXPLOT
        global data_type
        global selected_event_attribute
        values_1 = prepare_value_list_rel(values_1, "Categorical")
        values_2 = prepare_value_list_rel(values_2, "Continuous")

        fig_rel = {
            'data': [
                go.Box(
                boxpoints="all",
                x=values_1,
                y=values_2,
                marker=dict(color='red'),
                name="Change Pattern Value Differences")]
        } 
    return fig_rel


app =  DjangoDash(name='change_pattern_matrix', suppress_callback_exceptions=True, assets_folder="assets")

file_path = os.path.join(settings.MEDIA_ROOT, "change_patterns.csv")
file_path_relationships = os.path.join(settings.MEDIA_ROOT, "correlation_df.csv")
df = pd.DataFrame()
df_hm = pd.DataFrame()
x_axis = "E_At"
y_axis = "Rel"
effect_size = "RBC"
z_axis = "var"
data_type = "Continuous"
rel = "Eventually follows relations"
selected_rel_row = {}
rel_clicks = 0

x_val = []
y_val = []
z_val = []
x_all = []
y_all = []
z_all = []
init = True
data = []
annotation = []
config = {}
single_cell_df = pd.DataFrame()
event_log = []
image_counter = 0
corr_df = pd.DataFrame()

app.layout = html.Div([
    html.Div([     
        html.Img(id='image', src="/media/process_model.png", style={"max-width": "100%", "max-height": "100%"})
            ], style= {"width": "100%", "height": "50vh", "text-align":"center"}),


    dcc.Graph(id='heatmap', 
        figure = create_figure_con(x_val, y_val, data, annotation, "Event Attributes", "Relations")),
                html.Details([
            html.Summary("Configure Heatmap Output", style={"font-size": "20px", "font-family": "Arial", "background-color": "grey", "color":"white", "text-align":"center", "margin-top":"10px"}),
            html.Div([
                html.Div([
                dmc.Select(
                    data=["x-axis", "y-axis", "z-axis (Choose only one below!)"], 
                    label = "Select axis for event attributes",
                    value="x-axis", id='event_attribute_axis', 
                    style={"width": "20vh", "display":"inline-block"}
                ),
                dmc.Select(
                    data=["x-axis", "y-axis", "z-axis (Choose only one below!)"], 
                    label = "Select axis for relations",
                    value="y-axis", id='relation_axis', 
                    style={"width": "20vh", "display":"inline-block"}
                ),
                dmc.Select(
                    data=["x-axis", "y-axis", "z-axis (Choose only one below!)"], 
                    label = "Select axis for variants",
                    value="z-axis (Choose only one below!)", id='variant_axis', 
                    style={"width": "20vh", "display":"inline-block"}
                ),
                dmc.Select(
                    data=["Directly follows relations", "Eventually follows relations"], 
                    label = "Select relation type",
                    value="Eventually follows relations", id='selected_dfr_efr', 
                    style={"width": "15vh", "display":"inline-block"}
                ),
                dmc.Select(
                    data=["Continuous", "Categorical"], 
                    label = "Select data type to analyse",
                    value="Continuous", id='selected_con_cat', 
                    style={"width": "15vh", "display":"inline-block"}
                )
            ], style= {"width": "100vh", "display":"flex", "margin-left":"10px"}),

            html.Div([
                dmc.MultiSelect(
                label="Select Event Attributes",
                placeholder="No event attributes selected",
                id="selected_event_attributes",
                value=x_val,
                data=x_all,
                style={"width": "20vh", "display":"inline-block"},
            ),
            dmc.MultiSelect(
                label="Select Relations",
                placeholder="No relations selected",
                id="selected_relations",
                value=y_val,
                data=y_all,
                style={"width": "20vh", "display":"inline-block"},
            ),
            dmc.MultiSelect(
                label="Select Variants",
                placeholder="No variants selected",
                id="selected_variants",
                value=z_val,
                data=z_all,
                style={"width": "20vh", "display":"inline-block"},
            )
            ], style= {"width": "60", "display":"flex", "margin-left":"10px"}),  
            ])
        ], style= {"width": "100vh", "margin-left":"10px"}),
        html.Details([
            html.Summary("Analyse single change pattern", style={"font-size": "20px", "font-family": "Arial", "background-color": "grey", "color":"white", "text-align":"center", "margin-top":"10px"}),
            html.Div([
                dcc.Graph(id="single_cell_plot", figure = go.Figure())
            ]), 

            html.Div([
                dmc.Anchor(dmc.Button('Visualize selected cell in process model', id='update_process_model', color="orange"), href="/"),
                dmc.Button('Reset visualization configuration', id="reset_config", color="orange", style={"margin-left":"10px"}),
                dmc.Text(id="clicked_output_3", mt=10)

            ], style= {"width": "100vh", "display":"flex", "margin-left":"10px", "justify-content": "center", "align-items": "center"}),

            html.Details([
                html.Summary("Analyse relationships of selected cell", style={"font-size": "20px", "font-family": "Arial", "background-color": "grey", "color":"white", "text-align":"center", "margin-top":"10px"}),
                html.Div([
                    dmc.Text("Relationships of selected change pattern. Click one to plot the relationship below.", mt=10, style={"text-align":"center"}),
                    dash_table.DataTable(id="rel_table", data=pd.DataFrame().to_dict("records"))            
                ], style={"width":"95vh"}),
                html.Div([
                    dcc.Graph(id="rel_plot", figure = go.Figure())         
                ], style= {"width": "95vh"}),
                html.Div([
                    dmc.Anchor(dmc.Button('Visualize selected relationship in process model', id='update_process_model_rel', color="orange"), href="/") 
                ], style= {"width": "100vh", "display":"flex", "margin-left":"10px", "justify-content": "center", "align-items": "center"})
                
            ])


        ], style= {"width": "100vh", "margin-left":"10px"})
    ], style={"background-color":"#f5f5f5", "width":"100%"})

@app.callback(
        Output("image", "src"),
        Input("update_process_model", "n_clicks"),
        Input("update_process_model_rel", "n_clicks"),
        State("image", "src")
)

def update_process_model(n_clicks, rel_n_clicks, src):
    global config
    global event_log
    global image_counter
    global init
    global single_cell_df
    global selected_rel_row
    global rel_clicks
    if init == False:
        image_counter = image_counter + 1
    else:
        return "/media/process_model.png"
    

    single_cell_df = single_cell_df[["Rel", "E_At", "M1", "M2", "ST1", "ST2", "RBC", "Directly", "#Samples"]]
    ele = {}
    ele["M1"] = single_cell_df["M1"].round(2)
    ele["M2"] = single_cell_df["M2"].round(2)
    ele["E_At"] = single_cell_df["E_At"]
    ele["RBC"] = single_cell_df["RBC"].round(2)
    ele["Directly"] = single_cell_df["Directly"]
    ele["N"] = single_cell_df["#Samples"]

   
    #check if relationship button was clicked
    if rel_n_clicks is not None and rel_n_clicks > rel_clicks:
        rel_clicks = rel_n_clicks
        try:
            number_of_rels = len(config[single_cell_df["Rel"]]["strong"])
            ele["strong"] = config[single_cell_df["Rel"]]["strong"].copy()
            ele["strong"][number_of_rels] = {}
            ele["strong"][number_of_rels]["EA_1"] = selected_rel_row["measure_1"]
            ele["strong"][number_of_rels]["EA_2"] = selected_rel_row["measure_2"]
            ele["strong"][number_of_rels]["scipy_corr"] = selected_rel_row["R"]
        except Exception as error:
            ele["strong"] = {}
            ele["strong"][0] = {}
            ele["strong"][0]["EA_1"] = selected_rel_row["measure_1"]
            ele["strong"][0]["EA_2"] = selected_rel_row["measure_2"]
            ele["strong"][0]["scipy_corr"] = selected_rel_row["R"]
    
    config[single_cell_df["Rel"]] = ele

    dfg, sa, ea = pm4py.discover_directly_follows_graph(event_log)
    activities_count = pm4py.get_event_attribute_values(event_log, "concept:name")
    filter_df = pd.read_csv(os.path.join(settings.MEDIA_ROOT, "filter_df.csv"))
    act_filter = float(filter_df.iloc[0]["Act_Filter"])
    path_filter = float(filter_df.iloc[0]["Path_Filter"])
    dfg, sa, ea, activities_count = dfg_filtering.filter_dfg_on_activities_percentage(dfg, sa, ea, activities_count, act_filter)
    dfg, sa, ea, activities_count = dfg_filtering.filter_dfg_on_paths_percentage(dfg, sa, ea, activities_count, path_filter)
    param={}
    param["START_ACTIVITIES"] = sa
    param["END_ACTIVITIES"] = ea
    dfg_image = dfg_visualization.apply(dfg, att_config=config, log=event_log, variant=dfg_visualization.Variants.FREQUENCY, parameters = param)
    dfg_image_py = pgv.AGraph()
    dfg_image_py.read(dfg_image.save())
    img_src = "process_model_" + str(image_counter) + ".png"
    dfg_path = os.path.join(settings.MEDIA_ROOT, img_src)
    dfg_image_py.draw(dfg_path, prog="dot")
    return "/media/" + img_src

@app.callback(
        Output("clicked_output_3", "children"),
        Input("reset_config", "n_clicks"),
)

def reset_config(n_clicks):
    global config
    global init
    config = {}
    return ""


@app.callback(
        Output('selected_event_attributes', 'data'),
        Output('selected_event_attributes', 'value'),
        Output('selected_relations', 'data'),
        Output('selected_relations', 'value'),
        Output('selected_variants', 'data'),
        Output('selected_variants', 'value'),
        Input('selected_dfr_efr', 'value'),
        Input('selected_con_cat', 'value'),
)

def update_config_entries(selected_dfr_efr, selected_con_cat):
    global df
    global df_hm
    global x_val
    global y_val
    global z_val
    global x_all
    global y_all
    global z_all
    global init
    global data
    global annotation
    global effect_size
    global z_axis
    global event_log
    global file_path
    global file_path_relationships
    global corr_df
    if init == True:
        df = pd.read_csv(file_path)
        df["Rel"] = df["Act_1"] + ":" + df["Act_2"]
        df["RBC"] = -df["RBC"]
        df_hm = df.copy()
        df_hm = df.loc[df["Directly"] == False]
        try:
            df_hm = df_hm.loc[df_hm["Chi2"].isna()]
        except:
            pass

        x_val = list(df_hm.groupby(x_axis).count().sort_values("P", ascending=False).index)[:10]
        y_val = list(df_hm.groupby(y_axis).count().sort_values("P", ascending=False).index)[:10]
        z_val = list(df_hm.groupby(z_axis).count().sort_values("P", ascending=False).index)[:10]

        x_all = list(df_hm.groupby(x_axis).count().sort_values("P", ascending=False).index)
        y_all = list(df_hm.groupby(y_axis).count().sort_values("P", ascending=False).index)
        z_all = list(df_hm.groupby(z_axis).count().sort_values("P", ascending=False).index)
        data, annotation = fill_heatmap_data(x_axis, y_axis, z_axis, x_val, y_val, "ALL", df_hm, effect_size)
        file_path_event_log = os.path.join(settings.MEDIA_ROOT, "event_log.xes")
        event_log = pm4py.read_xes(file_path_event_log)
        try:
            corr_df = pd.read_csv(file_path_relationships)
            corr_df = corr_df.loc[
                               ((corr_df['scipy_corr'] > 0.6) | (corr_df['scipy_corr'] < -0.6)  |((corr_df["scipy_corr"] > 0.3) & (corr_df["method"] == "cramer")) |(corr_df["stat"] > 50)) & \
                               (corr_df['measure_1'] != corr_df['measure_2']) & (corr_df['sample_size'] > 50) \
                              ]
            corr_df["Rel"] = corr_df["Act_1"] + ":" + corr_df["Act_2"]
            corr_df.loc[corr_df["scipy_corr"].isna(), "scipy_corr"] = corr_df["stat"]
            corr_df.rename(columns={"Act_1" : "Activity 1", "Act_2" : "Activity 2", "sample_size":"Sample Size", "scipy_corr":"R"}, inplace=True)
        except:
            pass
        init = False

    if selected_con_cat == "Continuous":
        try:
            df_hm = df.loc[df["Chi2"].isna()]
        except:
            df_hm = df.copy()
        effect_size = "RBC"
    else:
        try:
            df_hm = df.loc[~df["Chi2"].isna()]
        except:
            df_hm = df.copy()
        effect_size = "Chi2"
    if selected_dfr_efr == "Directly follows relations":
        df_hm = df_hm.loc[df_hm["Directly"] == True]
    else:
        df_hm = df_hm.loc[df_hm["Directly"] == False]
    global data_type 
    global rel 
    data_type = selected_con_cat
    rel = selected_dfr_efr
    ea_all = list(df_hm.groupby("E_At").count().sort_values("P", ascending=False).index)
    rel_all = list(df_hm.groupby("Rel").count().sort_values("P", ascending=False).index)
    var_all = list(df_hm.groupby("var").count().sort_values("P", ascending=False).index)
    
    if z_axis == "E_At":
        return ea_all, [ea_all[0]], rel_all, rel_all[:10], var_all, var_all[:10]
    elif z_axis == "Rel":
        return ea_all, ea_all[:10], rel_all, [rel_all[0]], var_all, var_all[:10]
    else:
        return ea_all, ea_all[:10], rel_all, rel_all[:10], var_all, [var_all[0]]

@app.callback(
    Output('heatmap', 'figure'),
    Output('single_cell_plot','figure'),
    Output('rel_table', 'data'),
    Input('event_attribute_axis', 'value'),
    Input('relation_axis', 'value'),
    Input('variant_axis', 'value'),
    Input('selected_event_attributes', 'value'),
    Input('selected_relations', 'value'),
    Input('selected_variants', 'value'),
    Input('selected_dfr_efr', 'value'),
    Input('selected_con_cat', 'value'),
    Input('heatmap','clickData'),)

def update_figure(event_attribute_axis, relation_axis, variant_axis, selected_event_attributes, selected_relations, selected_variants, selected_dfr_efr, selected_con_cat, clickData):
    global x_val
    global y_val
    global x_axis
    global y_axis
    global z_axis
    global effect_size
    global data_type
    global z_val
    global df_hm
    global single_cell_df
    global corr_df
    global selected_event_attribute
    if not (event_attribute_axis != relation_axis and event_attribute_axis != variant_axis and relation_axis != variant_axis):
        #keep current config
        global data
        figure = create_figure_con(x_val, y_val, data, annotation, "Event Attributes", "Relations")
    else:
        if relation_axis == "x-axis":
            x_axis = "Rel"
            x_val = selected_relations
            x_title = "Relations"
        elif event_attribute_axis == "x-axis":
            x_axis = "E_At"
            x_val = selected_event_attributes
            x_title = "Event Attributes"
        elif variant_axis == "x-axis":
            x_axis = "var"
            x_val = selected_variants
            x_title = "Variants"
        if relation_axis == "y-axis":
            y_axis = "Rel"
            y_val = selected_relations
            y_title = "Relations"
        elif event_attribute_axis == "y-axis":
            y_axis = "E_At"
            y_val = selected_event_attributes
            y_title = "Event Attributes"
        elif variant_axis == "y-axis":
            y_axis = "var"
            y_val = selected_variants
            y_title = "Variants"
        if relation_axis == "z-axis (Choose only one below!)":
            z_axis = "Rel"
            z_val = selected_relations
        elif event_attribute_axis == "z-axis (Choose only one below!)":
            z_axis = "E_At"
            z_val = selected_event_attributes
        elif variant_axis == "z-axis (Choose only one below!)":
            z_axis = "var"
            z_val = selected_variants
        data, annotation = fill_heatmap_data(x_axis, y_axis, z_axis, x_val, y_val, z_val[0], df_hm, effect_size)
        if data_type == "Continuous":
            figure = create_figure_con(x_val, y_val, data, annotation, x_title, y_title)
        else: 
            figure = create_figure_cat(x_val, y_val, data, annotation, x_title, y_title)
    selected_relation = ""
    selected_event_attribute = ""
    selected_variant = ""
    try:  
        xnode = clickData['points'][0]['x']
        ynode = clickData['points'][0]['y']
        if x_axis == "Rel" and y_axis == "E_At" and z_axis == "var":
            selected_relation = xnode
            selected_event_attribute = ynode
            selected_variant = z_val
        elif x_axis == "Rel"and y_axis == "var" and z_axis == "E_At":
            selected_relation = xnode
            selected_event_attribute = z_val
            selected_variant = ynode
        elif x_axis == "E_At" and y_axis == "Rel" and z_axis == "var":
            selected_relation = ynode
            selected_event_attribute = xnode
            selected_variant = z_val         
        elif x_axis == "E_At" and y_axis == "var" and z_axis == "Rel":
            selected_relation = z_val
            selected_event_attribute = xnode
            selected_variant = ynode
        elif x_axis == "var" and y_axis == "Rel" and z_axis == "E_At":
            selected_relation = ynode
            selected_event_attribute = z_val
            selected_variant = xnode    
        elif x_axis == "var" and y_axis == "E_At" and z_axis == "Rel":
            selected_relation = z_val
            selected_event_attribute = ynode
            selected_variant = xnode             
        
        test = go.Scatter(mode="markers", x=[xnode], y=[ynode], marker_symbol=[5], hoverinfo='skip', hovertemplate=None, marker_size=20, marker_opacity=0.5, marker_color='White')

        figure["data"].append(test)
        y_title = "Samples"
        x_title = "Change Pattern Value Differences"
        #add trace here

        if data_type == "Continuous":
            single_cell_df = df_hm.loc[(df_hm[x_axis] == xnode) & (df[y_axis] == ynode) & (df[z_axis] == z_val[0])].iloc[0]
            val_1 = prepare_value_list(single_cell_df["Values_1"])
            val_2 = prepare_value_list(single_cell_df["Values_2"])
            val_dif = [(x-y) for (x,y) in zip(val_2, val_1)]
            fig_single_cell = {'data': [go.Histogram(histfunc="count",
                            x=val_dif,
                            marker=dict(color='rgb(253, 126, 20)'),
                            name="Change Pattern Value Differences")],
                    'layout': go.Layout(
                xaxis = dict(title = x_title),
                yaxis = dict(title = y_title),
                )
            }
        else:
            single_cell_df = df_hm.loc[(df_hm[x_axis] == xnode) & (df[y_axis] == ynode) & (df[z_axis] == z_val[0])].iloc[0]
            val_1 = prepare_value_list(single_cell_df["Values_1"])
            val_2 = prepare_value_list(single_cell_df["Values_2"])
            val_dif = [x + "-" + y for (x,y) in zip(val_1, val_2)]
            fig_single_cell = {'data': [go.Histogram(histfunc="count",
                            x=val_dif,
                            name="Change Pattern Value Differences")],
                    'layout': go.Layout(
                        xaxis = dict(title = x_title),
                        yaxis = dict(title = y_title),
                )
            }

            #fill dataframe here and plot for relationships
    except:
        fig_single_cell = go.Figure()
    try:
        if selected_dfr_efr == "Directly follows relations":   
            x = corr_df.loc[(corr_df["Rel"] == selected_relation) & ((corr_df["measure_1"] == selected_event_attribute) | (corr_df["measure_2"] == selected_event_attribute)) & (corr_df["Directly"] == True)]
        else:
            x = corr_df.loc[(corr_df["Rel"] == selected_relation) & ((corr_df["measure_1"] == selected_event_attribute) | (corr_df["measure_2"] == selected_event_attribute)) & (corr_df["Directly"] == False)]
    except:
        x = pd.DataFrame()
    global rel_table_data_complete
    rel_table_data_complete = x.copy()
    if len(rel_table_data_complete) > 0:
        rel_table_data_complete.reset_index(inplace=True)
        rel_table_data_complete.drop("index", axis=1, inplace=True)
        first_df = x.loc[x["measure_1"] != selected_event_attribute]
        first_df = first_df[["Activity 1", "Activity 2", "measure_1", "Sample Size", "P", "R", "method"]]
        first_df.rename(columns={"measure_1":"Related Attribute"}, inplace=True)
        second_df = x.loc[x["measure_2"] != selected_event_attribute]
        second_df = second_df[["Activity 1", "Activity 2", "measure_2", "Sample Size", "P", "R", "method"]]
        second_df.rename(columns={"measure_2":"Related Attribute"}, inplace=True)
        rel_table_data = pd.concat([first_df, second_df])
    else:
        rel_table_data = pd.DataFrame()
    return figure, fig_single_cell, rel_table_data.to_dict("records")


@app.callback(
    Output("rel_plot", "figure"),
    Input("rel_table", "active_cell")
)

def update_rel_plot(active_cell):
    global rel_table_data_complete
    global selected_rel_row
    row_id = active_cell["row"]
    selected_rel_row = rel_table_data_complete.iloc[row_id]

    return plot_cell_correlation(selected_rel_row)