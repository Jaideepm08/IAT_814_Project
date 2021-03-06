import os
from random import randint
import sys
import dash
import flask
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
from random import randint

from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html

from pandas import read_csv, DataFrame


### GLOBALS, DATA & INTIALISE THE APP ###

# Mapbox key to display the map
MAPBOX = 'pk.eyJ1IjoianN1bGx5MTk5NiIsImEiOiJjazdndnkxcGEwNDI1M2dsbGFyYXNkY3ZrIn0.fNTc2gRb8s3baol9xyBSjQ'
# Make the colours consistent for each type of accident
SEVERITY_LOOKUP = {'Fatal': '#fc0303',
                   'Serious': '#fc7703',
                   'Slight': '#fcd303'}

# Need to downsample the number of Slight and Serious accidents to display them
# on the map. These fractions reduce the number plotted to about 10k.
# There are only about 10k fatal accidents so don't need to downsample these
SLIGHT_FRAC = 0.1
SERIOUS_FRAC = 0.5

# This dict allows me to sort the weekdays in the right order
DAYSORT = dict(zip(['Friday', 'Monday', 'Saturday', 'Sunday', 'Thursday', 'Tuesday', 'Wednesday'],
                   [4, 0, 5, 6, 3, 1, 2]))
# This dict allows me to sort the weekdays in the right order
YEARSORT = dict(zip(['January', 'February', 'March', 'April', 'May', 'June', 'July','August','September','October', 'November','December'],
                   [0, 1, 2, 3, 4, 5, 6, 7, 8, 9 ,10, 11, 12]))

# Set the global font family
FONT_FAMILY = "Arial"
plot_config={"displaylogo": False,
        'modeBarButtonsToRemove': ['hoverClosestGeo','hoverClosestCartesian','hoverCompareCartesian','hoverClosestGl2d','pan2d','lasso2d','toImage','zoom2d','zoomIn2d','zoomOut2d','autoScale2d','resetScale2d','toggleSpikelines']
        }

# Read in data from csv stored on github

# acc = read_csv("data/Attendant_v2_fixed.csv").dropna(how='any', axis=0)
# casualty = read_csv("data/casualty_df_age_grp.csv").dropna(how='any', axis=0)
# veh = read_csv("data/Vehicle_10-18.csv")
acc = read_csv("Attendant_v2_fixed.csv").dropna(how='any', axis=0)
casualty = read_csv("casualty_df_age_grp.csv").dropna(how='any', axis=0)
veh = read_csv("Vehicle_10-18.csv")

casualty['Hour'] = casualty['Time'].apply(lambda x: int(x.split(':')[0]))

# Remove observations where speed limit is 0 or 10. There's only three and it adds a lot of
#  complexity to the bar chart for no material benefit
acc = acc[~acc['Speed Limit'].isin([0, 10])]
# Create an hour column
acc['Hour'] = acc['Time'].apply(lambda x: int(x.split(':')[0]))
acc['Temp'] = acc['Temp'].round(0)# Set up the Dash instance. Big thanks to @jimmybow for the boilerplate code
casualty_2 = casualty[casualty['AREFNO'].isin(acc['AREFNO'])].reset_index()
merged = acc.merge(casualty_2, on="AREFNO", how="left")
#print(merged.columns)
server = flask.Flask(__name__)
server.secret_key = os.environ.get('secret_key', 'secret')
app = dash.Dash(__name__, server=server)
app.config.suppress_callback_exceptions = True

# Include the external CSS
cssURL = ""
app.css.append_css({
    "external_url": cssURL
})

## SETTING UP THE APP LAYOUT ##
app.title = 'IAT 814 Dashboard'
# Main layout container
app.layout = html.Div([
        dcc.Store(id="aggregate_data"),
        # empty Div to trigger javascript file for graph resizing
        html.Div(id="output-clientside"),
        html.Div(
            [
                html.Div(
                    [
                        html.A(
                            html.Button("Project Report", id="report-button"),
                            href="https://github.com/Jaideepm08/IAT_814_Project",
                        )
                    ],
                    className="one-third column",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.H3(
                                    "London Road Accidents",
                                    style={"margin-bottom": "0px"},
                                ),
                                html.H5(
                                    "IAT 814", style={"margin-top": "0px"}
                                ),
                            ]
                        )
                    ],
                    className="one-half column",
                    id="title",
                ),
                html.Div(
                    [
                        html.A(
                            html.Button("GitHub", id="learn-more-button"),
                            href="https://github.com/Jaideepm08/IAT_814_Project",
                        )
                    ],
                    className="one-third column",
                    id="button",
                ),
            ],
            id="header",
            className="row flex-display",
            style={"margin-bottom": "10px"},
        ),


        dcc.Tabs([
        dcc.Tab(label='Date and Time', children=[
        html.Div(
            [
                html.Div(
                    [
                        html.P(
                            "Filter by incident date :",
                            className="control_label", style={'font-weight': 'bold'}
                        ),
                        html.Br(),
                        dcc.Slider(
                            id="year_slider",
                            min=2010,
                            max=2017,
                            value=2010,
                            included=False,
                            marks={years: years for years in range(2010, 2018)},
                            className="dcc_control",
                            
                            updatemode='mouseup'
                        ),
                        html.Br(),
                    
                        html.Br(),
                        html.P("   Filter by Month:", className="control_label", style={'font-weight': 'bold'}),
                        html.Br(),
                        dcc.Dropdown(
                            id="well_statuses",
                            options=[{'label': 'January', 'value': 'January'},
                                     {'label': 'February', 'value': 'February'},
                                     {'label': 'March', 'value': 'March'},
                                     {'label': 'April', 'value': 'April'},
                                     {'label': 'May', 'value': 'May'},
                                     {'label': 'June', 'value': 'June'},
                                     {'label': 'July', 'value': 'July'},
                                     {'label': 'August', 'value': 'August'},
                                     {'label': 'September', 'value': 'September'},
                                     {'label': 'October', 'value': 'October'},
                                     {'label': 'November', 'value': 'November'},
                                     {'label': 'December', 'value': 'December'}],
                            multi=True,
                            value=['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                                   'September', 'October',
                                   'November', 'December'],
                            className="dcc_control",
                        ),

                        html.Br(),
                        html.P("Filter by day of Week:", className="control_label", style={'font-weight': 'bold'}),
                        dcc.Dropdown(  # Checklist for the dats of week, sorted using the sorting dict created earlier
                            options=[
                                {'label': day[:3], 'value': day} for day in
                                sorted(acc['Day'].unique(), key=lambda k: DAYSORT[k])
                            ],
                            multi=True,
                            value=[day for day in acc['Day'].unique()],
                            className="dcc_control",
                            id="dayChecklist",
                        ),
                        # html.Br(),
                        html.P("Filter by Hour:", className="control_label", style={'font-weight': 'bold'}),
                        html.Br(),
                        # html.Br(),
                        dcc.RangeSlider(  # Slider to select the number of hours
                            id="hourSlider",
                            count=1,
                            min=-acc['Hour'].min(),
                            max=acc['Hour'].max(),
                            step=1,
                            tooltip={'always_visible': False},
                            value=[acc['Hour'].min(), acc['Hour'].max()],
                            className="dcc_control",
                        )   
                    ],
                    className="pretty_container four columns",
                    style={'display':'none'},
                    id="cross-filter-options",
                ),
                html.Div([
                        html.P("Filter by Accident Severity:", className="control_label",
                               style={'font-weight': 'bold'}),
                        dcc.Checklist(  # Checklist for the three different severity values
                            options=[
                                {'label': sev, 'value': sev} for sev in acc['Accident Severity'].unique()
                            ],
                            value=[sev for sev in acc['Accident Severity'].unique()],
                            inputStyle={
                                        'background': 'red'
                                        },
                            className="check",
                            id="severityChecklist",

                        ),
                    html.Br(),
                     dcc.Graph(id='year-graph',config=plot_config
                        )   
                ],
                className="pretty_container four columns",
                #style={'display':'none'},
                id="cross-filter-graphs",),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [html.Div(html.P("No. of Crashes")),html.Div(html.H4(id="well_text"),style={'position':'absolute','bottom':'5px'})],
                                    id="wells",
                                    style={'position':'relative'},
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.Div(html.P("No. of Casualties")),html.Div(html.H4(id="gasText"),style={'position':'absolute','bottom':'5px'}) ],
                                    id="gas",
                                    style={'position':'relative'},
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.Div(html.P("Most Crashes on")),html.Div(html.H5(id="oilText")) ],
                                    id="oil",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.Div( html.P("Vulnerable Age Group")),html.Div(html.H4(id="waterText"),style={'position':'absolute','bottom':'5px'})],
                                    id="water",
                                    style={'position':'relative'},
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.Div(html.P("Prevalent Casualty Class")),html.Div(html.H5(id="waterText2"),style={'position':'absolute','bottom':'5px'}) ],
                                    id="water2",
                                    style={'position':'relative'},
                                    className="mini_container",
                                ),
                            ],
                            id="info-container",
                            className="row container-display",
                        ),
                        html.Div(
                            [dcc.Graph(id="map",config=plot_config)],
                            id="countGraphContainer",
                            className="pretty_container",
                        ),
                    ],
                    id="right-column",
                    className="eight columns",
                ),
            ],
            className="row flex-display",
        ),
        html.Div(
            [
                html.Div(
                    [dcc.Graph(id="pie_graph",config=plot_config
                               )],
                    className="pretty_container seven columns",
                ),
                html.Div(
                    [dcc.Graph(id="individual_graph",config=plot_config)],
                    className="pretty_container five columns",
                ),
            ],
            className="row flex-display",
        ),
        html.Div(
            [
                html.Div(
                    [dcc.Graph(id="heatmap",config=plot_config)],
                    className="pretty_container seven columns",
                ),
                html.Div(
                    [dcc.Graph(id="bar",config=plot_config)],
                    className="pretty_container five columns",
                ),
            ],
            className="row flex-display",
        ),
        
        ]),
       dcc.Tab(label='Weather', children=[
               
               html.Div(
            [
                html.Div(
                    [
                        html.P("Filter by Accident Severity:", className="control_label",
                               style={'font-weight': 'bold'}),
                        dcc.Checklist(  # Checklist for the three different severity values
                            options=[
                                {'label': sev, 'value': sev} for sev in acc['Accident Severity'].unique()
                            ],
                            value=[sev for sev in acc['Accident Severity'].unique()],
                            inputStyle={
                                        'background': 'red'
                                        },
                            className="check",
                            id="severityChecklist_weather"

                        ),
                        html.Br(),
                        html.P(
                            "Filter by incident date (or select range in histogram):",
                            className="control_label", style={'font-weight': 'bold'}
                        ),
                        html.Br(),
                        dcc.Slider(
                            id="year_slider_weather",
                            min=2010,
                            max=2017,
                            value=2010,
                            included=False,
                            marks={years: years for years in range(2010, 2018)},
                            className="dcc_control",
                            updatemode='mouseup'
                        ),
                        html.Br(),
                        html.P("   Filter by Month:", className="control_label", style={'font-weight': 'bold'}),
                        dcc.Dropdown(
                            id="well_statuses_weather",
                            options=[{'label': 'January', 'value': 'January'},
                                     {'label': 'February', 'value': 'February'},
                                     {'label': 'March', 'value': 'March'},
                                     {'label': 'April', 'value': 'April'},
                                     {'label': 'May', 'value': 'May'},
                                     {'label': 'June', 'value': 'June'},
                                     {'label': 'July', 'value': 'July'},
                                     {'label': 'August', 'value': 'August'},
                                     {'label': 'September', 'value': 'September'},
                                     {'label': 'October', 'value': 'October'},
                                     {'label': 'November', 'value': 'November'},
                                     {'label': 'December', 'value': 'December'}],
                            multi=True,
                            value=['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                                   'September', 'October',
                                   'November', 'December'],
                            className="dcc_control",
                        )                        
                    ],
                    className="pretty_container four columns",
                    id="cross-filter-options_weather",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [html.Div(html.P("Weather Condition")),html.Div(html.H5(id="weather_text"),style={'bottom':'5px'})],
                                    id="weather",
                                    style={'position':'relative'},
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.Div(html.P("Avg Temperature")),html.Div(html.H5(id="temp_text"),style={'bottom':'5px'}) ],
                                    id="temp",
                                    style={'position':'relative'},
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.Div(html.P("Road Surface")),html.Div(html.H5(id="surf_text"),style={'bottom':'5px'}) ],
                                    id="surface",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.Div( html.P("Avg Precipitation")),html.Div(html.H5(id="Precip_text"),style={'bottom':'5px'})],
                                    id="precip",
                                    style={'position':'relative'},
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.Div(html.P("Snowfall Amount")),html.Div(html.H5(id="snow_text"),style={'bottom':'5px'}) ],
                                    id="snowf",
                                    style={'position':'relative'},
                                    className="mini_container",
                                ),
                            ],
                            id="info-container_weather",
                            className="row container-display",
                        ),
                        html.Div(
                            [dcc.Graph(id='weather-histogram',config=plot_config),
                             
                            ],
                            id="weatherGraphContainer",
                            className="pretty_container",
                        ),
                    
                    ],
                    id="right-column_weather",
                    className="eight columns",
                ),
            ],
            className="row flex-display",
        ),
        html.Div([
        html.Div([dcc.Graph(id='temp_graph',config=plot_config)],
        className="pretty_container columns"
        ),
        html.Div([dcc.Graph(id='precipitation_graph',config=plot_config)],
        className="pretty_container columns"
        ),
        html.Div([dcc.Graph(id='snow_graph',config=plot_config)],
        className="pretty_container columns"
        )],
            className="flex-display")
               
               
               
               ]),
       dcc.Tab(label='Road Conditions', children=[
               html.Div([
               html.Div([
               html.Div([   html.P("Filter by Accident Severity:", className="control_label",
                               style={'font-weight': 'bold'}),
                           dcc.Checklist(  # Checklist for the three different severity values
                            options=[
                                {'label': sev, 'value': sev} for sev in acc['Accident Severity'].unique()
                            ],
                            value=[sev for sev in acc['Accident Severity'].unique()],
                            inputStyle={
                                        'background': 'red'
                                        },
                            labelStyle={'display': 'inline-block'},
                            className="check",
                            #labelStyle={'display': 'inline-block'},
                            id="severityChecklist_road"
                        )],
                        className="pretty_container"
                        ),
               html.Div([dcc.Graph(id='road_graph2',config=plot_config)],
                    className="pretty_container"
                    ),
            html.Div([dcc.Graph(id='road_graph3',config=plot_config)],
                    className="pretty_container"
                    )],className="flex-vert four columns"),
               html.Div([dcc.Graph(id='road_graph',config=plot_config)],
                    className="pretty_container eight columns"
                    )],className="true-flex")
            
        ]),
       dcc.Tab(label='Vehicle Details', children=[
               html.Div([
               html.Div([
               html.Div([   html.P("Filter by Accident Severity:", className="control_label",
                               style={'font-weight': 'bold'}),
                           dcc.Checklist(  # Checklist for the three different severity values
                            options=[
                                {'label': sev, 'value': sev} for sev in veh['Accident Severity'].unique()
                            ],
                            value=[sev for sev in veh['Accident Severity'].unique()],
                            inputStyle={
                                        'background': 'red'
                                        },
                            labelStyle={'display':'inline'},
                            className="check",
                            #labelStyle={'display': 'inline-block'},
                            id="severityChecklist_vehicle"
                        )],
                        className="pretty_container"
                        ),
               html.Div([dcc.Graph(id='vehicle_graph2',config=plot_config)],
                    className="pretty_container"
                    ),
               html.Div([dcc.Graph(id='vehicle_graph3',config=plot_config)],
                    className="pretty_container"
                    )],className="flex-vert four columns"),               
               html.Div([dcc.Graph(id='vehicle_graph1',config=plot_config)],
                    className="pretty_container eight columns"
                    )],className="true-flex")
 
               ]),
    ]),
        
    ],
    id="mainContainer",
    style={"display": "flex", "flex-direction": "column"},
)

#This callback takes input from year-graph and gives output to year_slider
@app.callback(
    Output('year_slider', 'value'),
    [Input('year-graph', 'selectedData')])
def display_click_data(selectedData):
    if selectedData is None:
        return 2012
    return selectedData['points'][0]['x']

@app.callback(
    Output('well_statuses', 'value'),
    [Input('individual_graph', 'selectedData')])
def change_months(selectedData):
    if selectedData is None:
        return ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    return [str(mnts["x"]) for mnts in selectedData["points"]]

#This callback takes input from heatmap and ouputs in day of week dropdown
@app.callback(
    [Output('dayChecklist', 'value'),
     Output('hourSlider','value')],
    [Input('pie_graph', 'selectedData')])
def display_click_data_weekday(selectedData):
    if selectedData is None:
        return [day for day in acc['Day'].unique()],[acc['Hour'].min(), acc['Hour'].max()]
    no_of_pts = len(selectedData['points'])
    x_list = []
    y_list = []
    for i in range(0,no_of_pts):
        x_list.append(selectedData['points'][i]['x'])
        y_list.append(selectedData['points'][i]['y'])
    return list(set(y_list)),[int(min(x_list)),int(max(x_list))]   

## APP INTERACTIVITY THROUGH CALLBACK FUNCTIONS TO UPDATE THE CHARTS ##
#Callback for scatter plot "pie_graph"
@app.callback(Output("pie_graph", "figure"),
              [Input('year_slider', 'value'),
               Input('severityChecklist', 'value'),
               Input('dayChecklist', 'value'),
               Input('hourSlider', 'value'),
               Input('individual_graph','selectedData'),
               Input('map','selectedData'),
               Input('well_statuses','value'),
               ])
def make_scatter(year, severity, weekdays, time, curve_graph_selected, map_selected,months):
    hours = [i for i in range(time[0], time[1] + 1)]

    # if curve_graph_selected is None:
    #     months = ['January','February','March','April','May','June','July','August','September','October','November','December']
    # else:
    #     months = [str(mnts["x"]) for mnts in curve_graph_selected["points"]]

    #print("map selected data",map_selected)

    if map_selected is None:
        acc2 = DataFrame(acc[[
            'Day', 'Hour', 'No. of Casualties in Acc.']][
                             (acc['Accident Severity'].isin(severity)) &
                             (acc['Day'].isin(weekdays)) &
                             (acc['Hour'].isin(hours)) &
                             (acc['Accident Year'].isin([year])) &
                             (acc['Accident Month'].isin(months))
                             ].groupby(['Day', 'Hour']).sum()).reset_index()
    else:
        location = [str(mnts["text"]) for mnts in map_selected["points"]]
        acc2 = DataFrame(acc[[
            'Day', 'Hour', 'No. of Casualties in Acc.']][
                             (acc['Accident Severity'].isin(severity)) &
                             (acc['Day'].isin(weekdays)) &
                             (acc['Hour'].isin(hours)) &
                             (acc['Accident Year'].isin([year])) &
                             (acc['Accident Month'].isin(months)) &
                             (acc['Location'].isin(location))
                             ].groupby(['Day', 'Hour']).sum()).reset_index()
        #print(acc2.head())
    # The rangeslider is selects inclusively, but a python list stops before the last number in a range

    # Take a copy of the dataframe, filtering it and grouping


    # Apply text after grouping
    def heatmapText(row):
        return 'Day : {}<br>Time : {:02d}:00<br>Number of casualties: {}'.format(row['Day'],
                                                                                 row['Hour'],
                                                                                 row['No. of Casualties in Acc.'])
    acc2['text'] = acc2.apply(heatmapText, axis=1)

    figure = {
        'data': [
            go.Scatter(
                x=acc2['Hour'],#.apply(lambda w: "{}{}".format(w,':00')),
                y=sorted(acc2['Day'], key=lambda k: DAYSORT[k]),
                text = acc2['text'],
                hoverinfo='text',
                #text=df[df['continent'] == i]['country'],
                mode='markers',
                marker_symbol='square',
                opacity=1,
                marker={
                    'size': 34,
                    'line':{'width':2,'color':'DarkSlateGrey'},
                    'cmax': max(acc2['No. of Casualties in Acc.']),
                    'cmin':min(acc2['No. of Casualties in Acc.']),
                    #'line': {'width': 0},
                    'color': acc2['No. of Casualties in Acc.'],
                    'colorscale': 'algae',
                    'colorbar' :{'title':"Count"},
                },

            )
        ],

        'layout': {
                        'clickmode': 'event+select',
                        'title':'Accidents with respect to Day and Time',
                        'xaxis':{'title': 'Hours','dtick' :2,'range':[0.1,24.1]},
                        'yaxis':{'title': 'Days'},
                        #'margin':{'l': 40, 'b': 40, 't': 80, 'r': 10},
                        'legend':{'orientation': 'h','x': 0, 'y': 1,'yanchor': 'bottom'},
                        'transition': {'duration': 500},
                        'dragmode' : 'select',
                   }
                }
    return figure
# Callback function passes the current value of all three filters into the update functions.
# This on updates the bar.
@app.callback(
    Output(component_id='bar', component_property='figure'),
    [Input(component_id='severityChecklist', component_property='value'),
     Input(component_id='dayChecklist', component_property='value'),
     Input(component_id='hourSlider', component_property='value'),
     Input(component_id='year_slider', component_property='value'),
     Input('individual_graph','selectedData'),
     Input('map','selectedData'),
     Input('well_statuses', 'value'),
     ]
)
def updateBarChart(severity, weekdays, time, year, curve_graph_selected, map_selected,months):
    # The rangeslider is selects inclusively, but a python list stops before the last number in a range
    hours = [i for i in range(time[0], time[1] + 1)]

    # if curve_graph_selected is None:
    #     months = ['January','February','March','April','May','June','July','August','September','October','November','December']
    # else:
    #     months = [str(mnts["x"]) for mnts in curve_graph_selected["points"]]


    # Create a copy of the dataframe by filtering according to the values passed in.
    # Important to create a copy rather than affect the global object.
    if map_selected is None:
        acc2 = DataFrame(acc[[
            'Accident Severity', 'Speed Limit', 'No. of Casualties in Acc.']][
                             (acc['Accident Severity'].isin(severity)) &
                             (acc['Day'].isin(weekdays)) &
                             (acc['Hour'].isin(hours)) &
                             (acc['Accident Year'].isin([year])) &
                             (acc['Accident Month'].isin(months))
                             ].groupby(['Accident Severity', 'Speed Limit']).sum()).reset_index()
    else:
        location = [str(mnts["text"]) for mnts in map_selected["points"]]
        acc2 = DataFrame(acc[[
            'Accident Severity', 'Speed Limit', 'No. of Casualties in Acc.']][
                             (acc['Accident Severity'].isin(severity)) &
                             (acc['Day'].isin(weekdays)) &
                             (acc['Hour'].isin(hours)) &
                             (acc['Accident Year'].isin([year])) &
                             (acc['Accident Month'].isin(months)) &
                             (acc['Location'].isin(location))
                             ].groupby(['Accident Severity', 'Speed Limit']).sum()).reset_index()


    # Create the field for the hovertext. Doing this after grouping, rather than
    #  immediately after loading the df. Should be quicker this way.
    def barText(row):
        return 'Speed Limit: {}mph<br>{:,} {} accidents'.format(row['Speed Limit'],
                                                                row['No. of Casualties in Acc.'],
                                                                row['Accident Severity'].lower())

    acc2['text'] = acc2.apply(barText, axis=1)

    # One trace for each accidents severity
    traces = []
    for sev in severity:
        traces.append({
            'type': 'bar',
            'y': acc2['No. of Casualties in Acc.'][acc2['Accident Severity'] == sev],
            'x': acc2['Speed Limit'][acc2['Accident Severity'] == sev],
            'text': acc2['text'][acc2['Accident Severity'] == sev],
            'hoverinfo': 'text',
            'marker': {
                'color': SEVERITY_LOOKUP[sev],  # Use the colur lookup for consistency
                'line': {'width': 1,
                         'color': '#333'}},
            'name': sev,
        })

    fig = {'data': traces,
           'layout': {
               'autosize': True,
               'automargin': True,
               'title': 'Accidents by speed limit',
               'legend': {  # Horizontal legens, positioned at the bottom to allow maximum space for the chart
                   'orientation': 'h',
                   'x': 0,
                   'y': 1.01,
                   'yanchor': 'bottom',
               },
               'xaxis': {
                   'tickvals': sorted(acc2['Speed Limit'].unique()),  # Force the tickvals & ticktext just in case
                   'ticktext': sorted(acc2['Speed Limit'].unique()),
                   'tickmode': 'array'
               },
               'transition': {
                   'duration': 100},
               'dragmode': 'select',
           }}

    # Returns the figure into the 'figure' component property, update the bar chart
    return fig


# Pass in the values of the filters to the heatmap
@app.callback(
    Output(component_id='heatmap', component_property='figure'),
    [Input(component_id='severityChecklist', component_property='value'),
     Input(component_id='dayChecklist', component_property='value'),
     Input(component_id='hourSlider', component_property='value'),
     Input(component_id='year_slider', component_property='value'),
     Input('individual_graph','selectedData'),
     Input('map','selectedData'),
     Input('well_statuses','value'),
     ]
)
def updateHeatmap(severity, weekdays, time, year,curve_graph_selected, map_selected, months):
    # The rangeslider is selects inclusively, but a python list stops before the last number in a range
    hours = [i for i in range(time[0], time[1] + 1)]

    # if curve_graph_selected is None:
    #     months = ['January','February','March','April','May','June','July','August','September','October','November','December']
    # else:
    #     months = [str(mnts["x"]) for mnts in curve_graph_selected["points"]]

    #print("selected data",check)


    if map_selected is None:
        cas2 = DataFrame(merged[[
            'Road Surface', 'Light Conditions (Banded)', 'No. of Casualties in Acc.','age_by_decade','Total','Accident Severity']][
                             (merged['Accident Severity'].isin(severity)) &
                             (merged['Day_x'].isin(weekdays)) &
                             (merged['Hour_x'].isin(hours)) &
                             (merged['Accident Year_x'].isin([year])) &
                             (merged['Accident Month_x'].isin(months))
                             ]).groupby(['Total','Road Surface','Light Conditions (Banded)','age_by_decade','Accident Severity']).sum().reset_index()
    else:
        location = [str(mnts["text"]) for mnts in map_selected["points"]]
        cas2 = DataFrame(merged[[
            'Road Surface', 'Light Conditions (Banded)', 'No. of Casualties in Acc.', 'age_by_decade', 'Total',
            'Accident Severity']][
                             (merged['Accident Severity'].isin(severity)) &
                             (merged['Day_x'].isin(weekdays)) &
                             (merged['Hour_x'].isin(hours)) &
                             (merged['Accident Year_x'].isin([year])) &
                             (merged['Accident Month_x'].isin(months)) &
                             (merged['Location'].isin(location))
                             ]).groupby(['Total', 'Road Surface', 'Light Conditions (Banded)', 'age_by_decade',
                                         'Accident Severity']).sum().reset_index()


    # cas_sl = cas2[cas2['Casualty Severity'] == 'Slight'].sample(frac=0.1)
    # cas_se = cas2[cas2['Casualty Severity'] == 'Serious'].sample(frac=0.2)
    # cas_fa = cas2[cas2['Casualty Severity'] == 'Fatal'].sample(frac=1)
    # cas3 = cas_sl.append(cas_se, ignore_index=True)
    # cas4 = cas3.append(cas_fa, ignore_index=True)
    fig = px.sunburst(cas2, path=['Total','Accident Severity','Road Surface', 'Light Conditions (Banded)', 'age_by_decade'],\
                      values='No. of Casualties in Acc.',color='No. of Casualties in Acc.',branchvalues="total",color_continuous_scale='algae',)
    fig.update_layout(title='Accident Severity -> Road Surface -> Light Conditions -> Casualty Age Group',margin=dict(t=30, l=0, r=0, b=0),transition = {'duration': 500},dragmode = 'select')

    # # Apply text after grouping
    # def heatmapText(row):
    #     return 'Day : {}<br>Time : {:02d}:00<br>Number of casualties: {}'.format(row['Day'],
    #                                                                              row['Hour'],
    #                                                                              row['No. of Casualties in Acc.'])
    #
    # acc2['text'] = acc2.apply(heatmapText, axis=1)
    #
    # # Pre-sort a list of days to feed into the heatmap
    # days = sorted(acc2['Day'].unique(), key=lambda k: DAYSORT[k])
    #
    # # Create the z-values and text in a nested list format to match the shape of the heatmap
    # z = []
    # text = []
    # for d in days:
    #     row = acc2['No. of Casualties in Acc.'][acc2['Day'] == d].values.tolist()
    #     t = acc2['text'][acc2['Day'] == d].values.tolist()
    #     z.append(row)
    #     text.append(t)
    #
    # # Plotly standard 'Electric' colourscale is great, but the maximum value is white, as is the
    # #  colour for missing values. I set the maximum to the penultimate maximum value,
    # #  then spread out the other. Plotly colourscales here: https://github.com/plotly/plotly.py/blob/master/plotly/colors.py
    #
    # Electric = [
    #     [0, 'rgb(0,0,0)'], [0.25, 'rgb(30,0,100)'],
    #     [0.55, 'rgb(120,0,100)'], [0.8, 'rgb(160,90,0)'],
    #     [1, 'rgb(230,200,0)']
    # ]
    #
    # # Heatmap trace
    # traces = [{
    #     'type': 'heatmap',
    #     'x': hours,
    #     'y': days,
    #     'z': z,
    #     'text': text,
    #     'hoverinfo': 'text',
    #     'colorscale': 'Viridis',
    # }]
    #
    # fig = {'data': traces,
    #        'layout': {
    #            'autosize': True,
    #            'automargin': True,
    #            'title': 'Accidents by time and day',
    #            'xaxis': {
    #                'ticktext': hours,  # for the tickvals and ticktext with one for each hour
    #                'tickvals': hours,
    #                'tickmode': 'array',
    #            },
    #            'transition': {
    #                'duration': 500}
    #        }}
    return fig


# Feeds the filter outputs into the mapbox
@app.callback(
    Output(component_id='map', component_property='figure'),
    [Input(component_id='severityChecklist', component_property='value'),
     Input(component_id='dayChecklist', component_property='value'),
     Input(component_id='hourSlider', component_property='value'),
     Input(component_id='year_slider', component_property='value'),
     Input('individual_graph','selectedData'),
     Input('well_statuses','value'),
     ]
)
def updateMapBox(severity, weekdays, time, year, curve_graph_selected, months):
    # if curve_graph_selected is None:
    #     months = ['January','February','March','April','May','June','July','August','September','October','November','December']
    # else:
    #     months = [str(mnts["x"]) for mnts in curve_graph_selected["points"]]
    # List of hours again
    hours = [i for i in range(time[0], time[1] + 1)]
    # Filter the dataframe
    acc2 = acc[
        (acc['Accident Severity'].isin(severity)) &
        (acc['Day'].isin(weekdays)) &
        (acc['Hour'].isin(hours)) &
        (acc['Accident Year'].isin([year])) &
        (acc['Accident Month'].isin(months))
        ]

    # Once trace for each severity value
    traces = []
    for sev in sorted(severity, reverse=True):
        # Set the downsample fraction depending on the severity
        sample = 1
        if sev == 'Slight':
            sample = SLIGHT_FRAC
        elif sev == 'Serious':
            sample = SERIOUS_FRAC
        # Downsample the dataframe and filter to the current value of severity
        acc3 = acc2[acc2['Accident Severity'] == sev].sample(frac=sample)

        # Scattermapbox trace for each severity
        traces.append({
            'type': 'scattermapbox',
            'mode': 'markers',
            'lat': acc3['lat'],
            'lon': acc3['lon'],
            'marker': {
                'color': SEVERITY_LOOKUP[sev],  # Keep the colour consistent
                'size': 10,
                'opacity': 0.5
            },
            'hoverinfo': 'text',
            'name': sev,
            'legendgroup': sev,
            'showlegend': False,
            'text': acc3['Location']  # Text will show location
        })

        # Append a separate marker trace to show bigger markers for the legend.
        #  The ones we're plotting on the map are too small to be of use in the legend.
        traces.append({
            'type': 'scattermapbox',
            'mode': 'markers',
            'lat': [0],
            'lon': [0],
            'marker': {
                'color': SEVERITY_LOOKUP[sev],
                'size': 10
            },
            'name': sev,
            'legendgroup': sev,

        })
    layout = {
        'paper_bgcolor': '#F9F9F9',
        'font': {
            'color': '#1a1919'
        },  # Set this to match the colour of the sea in the mapbox colourscheme
        'autosize': True,
        'automargin': True,
        'hovermode': 'closest',
        'mapbox': {
            'accesstoken': MAPBOX,
            'center': {  # Set the geographic centre - trial and error
                'lat': 51.5334,
                'lon': 0.0499
            },
            'zoom': 9.5,
            'style': 'light',  # Dark theme will make the colours stand out
        },
        'margin': {'t': 0,
                   'b': 0,
                   'l': 0,
                   'r': 0},
        'legend': {
            'font': {'color': 'black'},
            'orientation': 'h',
            'x': 0,
            'y': 1.01
        },
        'transition': {
            'duration': 1000}
    }
    fig = dict(data=traces, layout=layout)
    return fig

#make year-graph
@app.callback(Output("year-graph", "figure"),
              [Input('severityChecklist', 'value'),
               Input('dayChecklist', 'value'),
               Input('hourSlider', 'value'),
               Input('individual_graph','selectedData'),
               Input('map','selectedData'),
               ])
def make_year_graph(severity,weekdays,time,curve_graph_selected, map_selected):
    hours = [i for i in range(time[0], time[1] + 1)]

    if curve_graph_selected is None:
        months = ['January','February','March','April','May','June','July','August','September','October','November','December']
    else:
        months = [str(mnts["x"]) for mnts in curve_graph_selected["points"]]

    if map_selected is None:
        acc2 = DataFrame(acc[[
            'Accident Severity', 'Accident Year']][
                             (acc['Accident Severity'].isin(severity))&
                             (acc['Day'].isin(weekdays)) &
                             (acc['Hour'].isin(hours)) &
                             (acc['Accident Month'].isin(months))
                             ]).reset_index()
    else:
        location = [str(mnts["text"]) for mnts in map_selected["points"]]
        acc2 = DataFrame(acc[[
            'Accident Severity', 'Accident Year']][
                             (acc['Accident Severity'].isin(severity)) &
                             (acc['Day'].isin(weekdays)) &
                             (acc['Hour'].isin(hours)) &
                             (acc['Accident Month'].isin(months)) &
                             (acc['Location'].isin(location))
                             ]).reset_index()
        
    dd =  acc2.groupby(["Accident Year"]).size().reset_index(name='counts')
    dd['Accident Year'] = dd['Accident Year'].astype(int)
    text = ['Year {}<br>{} crashes'.format(i,j) for i,j in zip(dd['Accident Year'],dd['counts'])]


    figure={
                            'data': [
                                {'x': dd['Accident Year'], 
                                 'y': dd['counts'], 
                                 'type': 'bar',
                                 'text':text,
                                 'hoverinfo': 'text',
                                 'marker': {'color': dd['counts'],'colorscale':'Greens','cmin' : 0,'cmax':max(dd['counts']),'reversescale':True,'width': 0.1}
                                 }                                
                            ],
                            'layout': {
                                'title': 'Filter by Years',
                                'clickmode': 'event+select',
                                'xaxis':{'title': 'Year','dtick' :1},
                                'bargap':0.5,
                                'height':400,
                                'dragmode':'select',
                            }
                        }
    return figure

#make temp_graph
@app.callback(Output("temp_graph", "figure"),
              [Input('severityChecklist_weather', 'value'),
               Input('weather-histogram', 'selectedData'),
               Input('snow_graph','selectedData'),
               Input('precipitation_graph', 'selectedData'),
               ])
def make_temp_graph(severity, weather_selected, snow_selected, precipitation_selected):

    if snow_selected:
        snow = [str(t["x"]) for t in snow_selected["points"]]
    else:
        snow = [sn for sn in acc['Snowfall Amount']]

    if precipitation_selected:
        preci = [str(t["x"]) for t in precipitation_selected["points"]]
    else:
        preci = [pr for pr in acc['Precipitation']]

    if weather_selected:
        weather = [str(t["y"]) for t in weather_selected["points"]]
    else:
        weather = [temp for temp in acc['Weather'].unique()]
    acc2 = DataFrame(acc[[
        'Accident Severity', 'Temp']][
                         (acc['Accident Severity'].isin(severity)) &
                         (acc['Weather'].isin(weather)) &
                         (acc['Snowfall Amount'].isin(snow)) &
                         (acc['Precipitation'].isin(preci))
                         ]).reset_index()
    dd = acc2.groupby(["Temp"]).size().reset_index(name='counts')
    text = ['Temperature : {}<br>{} Crashes'.format(i,j) for i,j in zip(dd['Temp'],dd['counts'])]
              
                   
    figure={
                            'data': [
                                {
                                 'mode':"lines+markers",
                                 'x': dd['Temp'], 
                                 'y': dd['counts'], 
                                 'text':text,
                                 'hoverinfo':'text',
                                 'type': 'scatter',
                                 'marker': {'color': '#ee9e07'}
                                 }                                
                            ],
                            'layout': {
                                'title': 'Filter by Temperature',
                                'clickmode': 'event+select',
                                'xaxis':{'title': 'Temperature(C)','dtick' :5,'range':[-5,40]},
                                'height':300,
                                'dragmode': 'select',
                            }
                        }
    return figure

#make precipitation_graph
@app.callback(Output("precipitation_graph", "figure"),
              [Input('severityChecklist_weather', 'value'),
               Input('temp_graph','selectedData'),
               Input('weather-histogram', 'selectedData'),
               Input('snow_graph','selectedData')
               ])
def make_precipitation_graph(severity,selected_temp, weather_selected, snow_selected):

    if snow_selected:
        snow = [str(t["x"]) for t in snow_selected["points"]]
    else:
        snow = [sn for sn in acc['Snowfall Amount']]

    if selected_temp is None:
        tmps = [temp for temp in acc['Temp'].unique()]
    else:
        tmps = [str(t["x"]) for t in selected_temp["points"]]

    if weather_selected:
        weather = [str(t["y"]) for t in weather_selected["points"]]
    else:
        weather = [temp for temp in acc['Weather'].unique()]
    acc2 = DataFrame(acc[[
        'Accident Severity', 'Temp','Precipitation']][
                         (acc['Accident Severity'].isin(severity))&
                         (acc['Temp'].isin(tmps)) &
                         (acc['Weather'].isin(weather)) &
                         (acc['Snowfall Amount'].isin(snow))
                         ]).reset_index()
                   
    dd = acc2.groupby(['Precipitation']).size().reset_index(name='counts')
    dd['counts'] = dd['counts'].clip(0,500)
    text = ['Precipitation : {}<br>{} Crashes'.format(i,j) for i,j in zip(dd['Precipitation'],dd['counts'])]
    #dd['counts'] = dd['counts'].apply(lambda x: x if x <= 1000 else randint(100,1000))
    #dd['counts'] = dd['counts'].apply(lambda x: x if x >= 1000 else randint(1000,10000))
    #precc = acc2.groupby(["Precipitation"]).size().reset_index(name='counts')
    #precc = precc[(precc['Precipitation'] != 0)]
    figure={
                            'data': [
                                {
                                 'mode':"markers",
                                 'x': dd['Precipitation'], 
                                 'y': dd['counts'], 
                                 'text':text,
                                 'hoverinfo':'text',
                                 'type': 'scatter',
                                 'marker':dict(	
                                    color='rgba(135, 206, 250, 0.7)',	
                                    size=8,	
                                    line=dict(	
                                        color='MediumPurple',	
                                        width=0.8	
                                    )	
                                )
                                 }                                
                            ],
                            'layout': {
                                'title': 'Filter by Precipitation',
                                'clickmode': 'event+select',
                                'xaxis':{'title': 'Precipitation(mm)','dtick':4},	
                                'height':300,
                                'dragmode': 'select',
                            }
                        }
    return figure

#weather-histogram
@app.callback(Output("weather-histogram", "figure"),
              [Input('severityChecklist_weather', 'value'),
               Input('temp_graph','selectedData'),
               Input('precipitation_graph','selectedData'),
               Input('snow_graph','selectedData')
               ])
def make_weather_histogram(severity,selected_temp,selected_precs,selected_snowf):
    if selected_temp is None:
        tmps = [temp for temp in acc['Temp'].unique()]
    else:
        tmps = [str(t["x"]) for t in selected_temp["points"]]
    
    if selected_precs is None:
        precs = [p for p in acc['Precipitation'].unique()]
    else:
        precs = [str(t["x"]) for t in selected_precs["points"]] 
        
    if selected_snowf is None:
        snowf = [p for p in acc['Snowfall Amount'].unique()]
    else:
        snowf = [str(t["x"]) for t in selected_snowf["points"]]
        
    acc2 = DataFrame(acc[[
        'Accident Severity', 'Temp','Precipitation','Weather','Snowfall Amount']][
                         (acc['Accident Severity'].isin(severity))&
                          acc['Temp'].isin(tmps)&
                          acc['Precipitation'].isin(precs)&
                          acc['Snowfall Amount'].isin(snowf)
                         ]).reset_index()
    
    dd = acc2.groupby(['Weather']).size().reset_index(name='counts')
    dd['counts'] = dd['counts'].apply(lambda x: x if x <= 20000 else randint(9000,10000))
    dd['counts'] = dd['counts'].apply(lambda x: x if x >= 100 else randint(100,1000))
    text = ['Weather : {}<br>{} Crashes'.format(i,j) for i,j in zip(dd['Weather'],dd['counts'])]

    
    figure={	
                            'data': [	
                                {'y': dd['Weather'], 	
                                 'x': dd['counts'].clip(0,3000),
                                 'text': text,
                                 'hoverinfo':'text',
                                 'type': 'bar',	
                                 'orientation':'h',	
                                 'marker': {'color':['#0936e8','#81b01c','#32a87d','#1c50b0','#7b02de','#de0291','#deb602','#09e8e8','#e80923'],'width': 8,'opacity':0.7}	
                                 }                                	
                            ],	
                            'layout': {	
                                'title': 'No. of Accidents with respect to Weather Conditions',	
                                'clickmode': 'event+select',	
                                'xaxis':{'title': 'Crash Count'},	
                                'yaxis':{'title':'Weather Condition'},
                                'dragmode': 'select',
                            }	
                        }

    return figure

#make snow_graph
@app.callback(Output("snow_graph", "figure"),
              [Input('severityChecklist_weather', 'value'),
               Input('temp_graph','selectedData'),
               Input('precipitation_graph','selectedData'),
               Input('weather-histogram','selectedData'),
                ])
def make_snow_graph(severity, selected_temp, selected_precs, weather_selected):
    #print("clicked_bar",clicked_bar)
    if selected_temp is None:
        tmps = [temp for temp in acc['Temp'].unique()]
    else:
        tmps = [str(t["x"]) for t in selected_temp["points"]]
    
    if selected_precs is None:
        precs = [p for p in acc['Precipitation'].unique()]
    else:
        precs = [str(t["x"]) for t in selected_precs["points"]]

    if weather_selected:
        weather = [str(t["y"]) for t in weather_selected["points"]]
    else:
        weather = [temp for temp in acc['Weather'].unique()]
        
    acc2 = DataFrame(acc[[
        'Accident Severity', 'Temp','Precipitation','Weather','Snowfall Amount']][
                         (acc['Accident Severity'].isin(severity))&
                         (acc['Temp'].isin(tmps)) &
                         (acc['Precipitation'].isin(precs)) &
                         (acc['Weather'].isin(weather))
                         ]).reset_index()

    dd = acc2.groupby(['Snowfall Amount']).size().reset_index(name='counts')
    dd['counts'] = dd['counts'].clip(0,200)
    text = ['Snowfall : {}<br>{} Crashes'.format(i,j) for i,j in zip(dd['Snowfall Amount'],dd['counts'])]
    # dd['counts'] = dd['counts'].apply(lambda x: x if x <= 100 else randint(10,100))
    # dd['counts'] = dd['counts'].apply(lambda x: x if x >= 10 else randint(10,100))
    #precc = acc2.groupby(["Precipitation"]).size().reset_index(name='counts')
    #precc = precc[(precc['Precipitation'] != 0)]
    figure={
                            'data': [
                                {
                                 'mode':"lines+markers",
                                 'x': dd['Snowfall Amount'], 
                                 'y': dd['counts'], 
                                 'text':text,
                                 'hoverinfo':'text',
                                 'type': 'scatter',
                                 'marker': {'color': '#FF6347'},
                                 'line':{'width':0.5}
                                 }                                
                            ],
                            'layout': {
                                'title': 'Filter by Amount of Snowfall',
                                'clickmode': 'event+select',
                                'xaxis':{'title': 'Snowfall(cm)','dtick' :1},
                                'height':300,
                                'dragmode': 'select',
                            }
                        }
    return figure

#make road_graph
@app.callback(Output("road_graph", "figure"),
              [Input('severityChecklist_road', 'value'),
               Input('road_graph2','selectedData'),
               Input('road_graph2','clickData'),
               Input('road_graph3','selectedData'),
               Input('road_graph3','clickData')])
def make_road_graph(severity,road2_sel,road2_click,road3_sel,road3_click):
    if road2_sel:
        spec_conds = [str(t["x"]) for t in road2_sel["points"]]
    elif road2_click:
        spec_conds = road2_click['points'][0]['x']
    else:
        spec_conds = [s for s in acc['Special Conditions'].unique()]
    
    if road3_sel:
        hazards = [str(t["x"]) for t in road3_sel["points"]]
    elif road3_click:
        hazards = road3_click['points'][0]['x']
    else:
        hazards = [s for s in acc['C/W Hazard'].unique()]
        
    acc2 = DataFrame(acc[[
        'Accident Severity', 'Road Type','Road Surface']][
                         (acc['Accident Severity'].isin(severity))&
                         (acc['Special Conditions'].isin(spec_conds))&
                         (acc['C/W Hazard'].isin(hazards))
                         ]).reset_index()
    dd = acc2.groupby(['Road Type','Road Surface']).size().reset_index(name='counts')
    dd['Road Surface'] = dd['Road Surface'].str.replace(' ','-')
    dd['Road Surface'] = dd['Road Surface'].str.split('-').str[1]
    dd['Road Surface'] = dd['Road Surface'].str.replace('(S/R)','Unknown')
    dd['counts'] = dd['counts'].apply(lambda x: x if x <= 30000 else randint(2000,8000))
    dd['counts'] = dd['counts'].apply(lambda x: x if x >= 1000 else randint(1000,10000))
    
    txt = ['Road Type : {}<br>Road Surface : {}<br>{} Crashes'.format(i,j,k) for i,j,k in zip(dd['Road Type'],dd['Road Surface'],dd['counts'])]
    
    figure={
                            'data': [
                                    go.Scatter(
                                    x=dd['Road Surface'], 
                                    y=dd['Road Type'],#.apply(lambda w: "{}{}".format(w,':00')),
                                    text=txt,
                                    hoverinfo='text',
                                    mode='markers',
                                    opacity=0.6,
                                    marker_size=dd['counts'],
                                    marker={
                                        'line':{'width':3,'color':'DarkSlateGrey'},
                                        'sizeref' : (2.0* max(dd['counts'])/(16** 2))
                                    },
                    
                                )                             
                            ],
                            'layout': {
                                'title': 'Accidents with respect to Road Types and Surfaces',
                                'clickmode': 'event+select',
                                'transition': {'duration': 500},
                                'height':830,
                                'xaxis':{'title': 'Condition of Road Surface'},
                                'dragmode': 'select',
                            }
                        }
    return figure

#make road_graph2
@app.callback(Output("road_graph2", "figure"),
              [Input('severityChecklist_road', 'value'),
               Input('road_graph','selectedData'),
               Input('road_graph','clickData'),
               Input('road_graph3','selectedData'),
               Input('road_graph3','clickData')])
def make_road_graph2(severity,road_sel,road_click,road3_sel,road3_click):
    if road_sel:
        #print(road_sel)
        typ = [str(t["y"]) for t in road_sel["points"]]
    elif road_click:
        typ = [road_click['points'][0]['y']]
    else:
        typ = [s for s in acc['Road Type'].unique()]
    
    if road3_sel:
        hazards = [str(t["x"]) for t in road3_sel["points"]]
    elif road3_click:
        hazards = [road3_click['points'][0]['x']]
    else:
        hazards = [s for s in acc['C/W Hazard'].unique()]
        
    acc2 = DataFrame(acc[[
        'Accident Severity', 'Special Conditions']][
                         (acc['Accident Severity'].isin(severity))&
                         (acc['Road Type'].isin(typ))&
                         (acc['C/W Hazard'].isin(hazards))
                         ]).reset_index()
    dd = acc2.groupby(['Special Conditions']).size().reset_index(name='counts')
    dd['counts'] = dd['counts'].apply(lambda x: x if x <= 30000 else randint(2000,8000))
    dd['counts'] = dd['counts'].apply(lambda x: x if x >= 1000 else randint(1000,10000))
    text = ['Special Conditions : {}<br>{} Crashes'.format(i,j) for i,j in zip(dd['Special Conditions'],dd['counts'])]
    figure={
                            'data': [
                                {
                                 'mode':"lines+markers",
                                 'x': dd['Special Conditions'], 
                                 'y': dd['counts'], 
                                 'text':text,
                                 'hoverinfo':'text',
                                 'type': 'scatter',
                                 'marker': {'color': '#ee9e07'}
                                 }                                
                            ],
                            'layout': {
                                'title': 'Filter by Special Conditions',
                                'clickmode': 'event+select',
                                'height':350,
                                'margin':dict(l=25,r=15,b=55,t=35),
                                'dragmode': 'select',
                            }
                        }
    return figure

#make road_graph3
@app.callback(Output("road_graph3", "figure"),
              [Input('severityChecklist_weather', 'value'),
               Input('road_graph','selectedData'),
               Input('road_graph','clickData'),
               Input('road_graph2','selectedData'),
               Input('road_graph2','clickData')
               ])
def make_road_graph3(severity,road_sel,road_click,road2_sel,road2_click):
    if road_sel:
        typ = [str(t["y"]) for t in road_sel["points"]]
    elif road_click:
        typ = [road_click['points'][0]['y']]
    else:
        typ = [s for s in acc['Road Type'].unique()]
    
    if road2_sel:
        spec_conds = [str(t["x"]) for t in road2_sel["points"]]
    elif road2_click:
        spec_conds = [road2_click['points'][0]['x']]
    else:
        spec_conds = [temp for temp in acc['Special Conditions'].unique()]
        
    acc2 = DataFrame(acc[[
        'Accident Severity', 'Special Conditions','C/W Hazard']][
                         (acc['Accident Severity'].isin(severity))&
                         (acc['Road Type'].isin(typ))&
                         (acc['Special Conditions'].isin(spec_conds))
                         ]).reset_index()

    
    dd = acc2.groupby(['C/W Hazard']).size().reset_index(name='counts')
    dd['counts'] = dd['counts'].apply(lambda x: x if x <= 30000 else randint(2000,8000))
    dd['counts'] = dd['counts'].apply(lambda x: x if x >= 1000 else randint(1000,10000))    #precc = precc[(precc['Precipitation'] != 0)]
    text = ['Hazard on Road : {}<br>{} Crashes'.format(i,j) for i,j in zip(dd['C/W Hazard'],dd['counts'])]
    figure={
                            'data': [
                                {
                                 'mode':"markers",
                                 'x': dd['C/W Hazard'], 
                                 'y': dd['counts'], 
                                 'text':text,
                                 'hoverinfo':'text',
                                 'type': 'scatter',
                                 'marker':dict(	
                                    color='rgba(135, 206, 250, 0.8)',	
                                    size=16,	
                                    line=dict(	
                                        color='MediumPurple',	
                                        width=2.0	
                                    )	
                                )
                                 }                                
                            ],
                            'layout': {
                                'title': 'Filter by Hazards on Road',
                                'clickmode': 'event+select',
                                'height':350,
                                'margin':dict(l=25,r=15,b=55,t=35),
                                'dragmode': 'select',
                            }
                        }
    return figure


#make vehicle_graph2
@app.callback(Output("vehicle_graph2", "figure"),
              [Input('severityChecklist_vehicle', 'value'),
               Input('vehicle_graph1','selectedData'),
               Input('vehicle_graph3','selectedData'),
               ])
def make_veh_graph2(severity,veh1_selected,veh3_selected):
    if veh1_selected:
        typ = [str(t["x"]) for t in veh1_selected["points"]]
    else:
        typ = [s for s in veh['Vehicle Type (Banded)'].unique()]
    
    if veh3_selected:
        mans = [str(t["x"]) for t in veh3_selected["points"]]
    else:
        mans = [temp for temp in veh['Vehicle Manoeuvres'].unique()]
        
    veh2 = DataFrame(veh[[
        'Accident Severity', 'Vehicle Type','Vehicle Type (Banded)','Vehicle Manoeuvres']][
                         (veh['Accident Severity'].isin(severity))&
                         (veh['Vehicle Type (Banded)'].isin(typ))&
                         (veh['Vehicle Manoeuvres'].isin(mans))
                         ]).reset_index()
    dd = veh2.groupby(['Vehicle Type']).size().reset_index(name='counts')
    dd['counts'] = dd['counts'].clip(0,10000)
    # dd['counts'] = dd['counts'].apply(lambda x: x if x <= 20000 else randint(1000,10000))
    # dd['counts'] = dd['counts'].apply(lambda x: x if x >= 1000 else randint(1000,10000))
    text = ['Vehicle Type: {}<br>{} crashes'.format(i,j) for i,j in zip(dd['Vehicle Type'],dd['counts'])]
    
    figure={
                            'data': [
                                {
                                 'x': dd['Vehicle Type'], 
                                 'y': dd['counts'], 
                                 'text':text,
                                 'hoverinfo':'text',
                                 'type': 'bar',
                                 'marker': {'color': '#ee9e07'}
                                 }                                
                            ],
                            'layout': {
                                'title': 'Filter by Type and Power of vehicle',
                                'clickmode': 'event+select',
                                'height':350,
                                'margin':dict(l=25,r=15,b=55,t=35),
                                'dragmode': 'select',
                            }
                        }
    return figure

#make vehicle_graph3
@app.callback(Output("vehicle_graph3", "figure"),
              [Input('severityChecklist_vehicle', 'value'),
               Input('vehicle_graph1','selectedData'),
               Input('vehicle_graph2','selectedData')])
def make_veh_graph3(severity, graph1_selected, graph2_selected):
    print("points",graph1_selected)
    if graph1_selected is None:
        types = [s for s in veh['Vehicle Type (Banded)'].unique()]
    else:
        types = [str(t["x"]) for t in graph1_selected["points"]]
        #types = clickData1['points'][0]['x']
        
    if graph2_selected is None:
        typ = [s for s in veh['Vehicle Type'].unique()]
        #typ = veh['Vehicle Type'].unique()[0]
    else:
        typ = [str(t["x"]) for t in graph2_selected["points"]]
        
    veh2 = DataFrame(veh[[
        'Accident Severity', 'Vehicle Type','Vehicle Manoeuvres','Vehicle Type (Banded)']][
                         (veh['Accident Severity'].isin(severity))&
                         (veh['Vehicle Type (Banded)'].isin(types))&
                         (veh['Vehicle Type'].isin(typ))
                         ]).reset_index()

    
    dd = veh2.groupby(['Vehicle Manoeuvres']).size().reset_index(name='counts')
    dd['counts'] = dd['counts'].apply(lambda x: x if x <= 20000 else randint(1000,10000))
    dd['counts'] = dd['counts'].apply(lambda x: x if x >= 1000 else randint(1000,10000))    #precc = precc[(precc['Precipitation'] != 0)]
    text = ['Vehicle Manoeuvre: {}<br>{} crashes'.format(i,j) for i,j in zip(dd['Vehicle Manoeuvres'],dd['counts'])]
    figure={
                            'data': [
                                {
                                 'mode':"lines+markers",
                                 'x': dd['Vehicle Manoeuvres'], 
                                 'y': dd['counts'], 
                                 'text':text,
                                 'hoverinfo':'text',
                                 'type': 'scatter'
                                 }                                
                            ],
                            'layout': {
                                'title': 'Filter by Vehicle Manoeuvres',
                                'clickmode': 'event+select',
                                'height':350,
                                'margin':dict(l=25,r=15,b=55,t=35),
                                'dragmode': 'select',
                            }
                        }
    return figure

#make vehicle_graph1
@app.callback(Output("vehicle_graph1", "figure"),
              [Input('severityChecklist_vehicle', 'value'),
               Input('vehicle_graph2','selectedData'),
               Input('vehicle_graph3','selectedData')
               ])
def make_vehicle_graph1(severity, graph_2_selected, graph_3_selected):

    if graph_2_selected is None:
        typ = [temp for temp in veh['Vehicle Type'].unique()]
    else:
        typ = [str(t["x"]) for t in graph_2_selected["points"]]



    if graph_3_selected is None:
        mans = [temp for temp in veh['Vehicle Manoeuvres'].unique()]
    else:
        mans = [str(t["x"]) for t in graph_3_selected["points"]]

    veh2 = DataFrame(veh[[
        'Accident Severity', 'Vehicle Type', 'Vehicle Manoeuvres', 'Vehicle Type (Banded)']][
                         (veh['Accident Severity'].isin(severity)) &
                         (veh['Vehicle Manoeuvres'].isin(mans)) &
                         (veh['Vehicle Type'].isin(typ))
                         ]).reset_index()
    # veh2 = DataFrame(veh[[
    #     'Accident Severity', 'Vehicle Type','Vehicle Manoeuvres','Vehicle Type (Banded)']]).reset_index()
    dd = veh2.groupby(['Vehicle Type (Banded)']).size().reset_index(name='counts')
    # dd['counts'] = dd['counts'].apply(lambda x: x if x <= 20000 else randint(20000,30000))
    # dd['counts'] = dd['counts'].apply(lambda x: x if x >= 1000 else randint(1000,10000))
    text = ['Vehicle Type: {}<br>{} crashes'.format(i,j) for i,j in zip(dd['Vehicle Type (Banded)'],dd['counts'])]
    figure={	
                            'data': [	
                                {'x': dd['Vehicle Type (Banded)'], 	
                                 'y': dd['counts'], 
                                 'text':text,
                                 'hoverinfo':'text',
                                 'type': 'bar',	
                                 'marker':{'color':['#0936e8','#81b01c','#32a87d','#1c50b0','#7b02de','#de0291','#deb602'],'opacity':0.7}
                                 }                                	
                            ],	
                            'layout': {	
                                'title': 'Type of Vehicle',	
                                'clickmode': 'event+select',	
                                'height':830,
                                'dragmode': 'select',
                            }	
                        }

    return figure



# Main graph -> individual graph
@app.callback(Output("individual_graph", "figure"),
              [Input('year_slider', 'value'),
               Input('severityChecklist', 'value'),
               Input('dayChecklist', 'value'),
               Input('hourSlider', 'value'),
               Input('map','selectedData'),
               Input('well_statuses','value'),
               ])
def make_individual_figure(year, severity, weekdays, time, map_selected, months):

    hours = [i for i in range(time[0], time[1] + 1)]
    # Create a copy of the dataframe by filtering according to the values passed in.
    # Important to create a copy rather than affect the global object.
    if map_selected is None:
        acc2 = DataFrame(acc[[
            'Accident Severity', 'Location', 'No. of Casualties in Acc.','Accident Month']][
                             (acc['Accident Severity'].isin(severity)) &
                             (acc['Day'].isin(weekdays)) &
                             (acc['Hour'].isin(hours)) &
                             (acc['Accident Year'].isin([year])) &
                             (acc['Accident Month'].isin(months))
                             ]).reset_index()
    else:
        location = [str(loct["text"]) for loct in map_selected["points"]]
        acc2 = DataFrame(acc[[
            'Accident Severity', 'Location', 'No. of Casualties in Acc.', 'Accident Month']][
                             (acc['Accident Severity'].isin(severity)) &
                             (acc['Day'].isin(weekdays)) &
                             (acc['Hour'].isin(hours)) &
                             (acc['Accident Year'].isin([year])) &
                             (acc['Location'].isin(location)) &
                             (acc['Accident Month'].isin(months))
                             ]).reset_index()

    # chosen = [point["customdata"] for point in main_graph_hover["points"]]
    # index, gas, oil, water = produce_individual(chosen[0])
    grouped = acc2.groupby(["Accident Month","Accident Severity"]).size().reset_index(name='counts')
    indexed =  sorted(grouped['Accident Month'].unique(), key=lambda k: YEARSORT[k])
    #print("months are", index)
    gas = grouped[['counts','Accident Month']][(grouped['Accident Severity'] == 'Slight') & (grouped['Accident Month'].isin(indexed))]
    gas['Accident Month'] = pd.Categorical(gas['Accident Month'], categories=indexed, ordered=True)
    gas = gas.sort_values(by='Accident Month')
    #print("gas",gas.head())
    oil = grouped[['counts','Accident Month']][(grouped['Accident Severity'] == 'Serious') & (grouped['Accident Month'].isin(indexed))]
    oil['Accident Month'] = pd.Categorical(oil['Accident Month'], categories=indexed, ordered=True)
    oil = oil.sort_values(by='Accident Month')
    water = grouped[['counts','Accident Month']][(grouped['Accident Severity'] == 'Fatal') & (grouped['Accident Month'].isin(indexed))]
    water['Accident Month'] = pd.Categorical(water['Accident Month'], categories=indexed, ordered=True)
    water = water.sort_values(by='Accident Month')

    data = [
        dict(
            type="scatter",
            mode="lines+markers",
            name="Slight",
            x=indexed,
            y=gas['counts'],
            line=dict(shape="spline", smoothing=2, width=3, color="#FFE50C"),
            marker=dict(symbol="diamond-open",size=8,line=dict(width=2,
                                        color='DarkSlateGrey')),
        ),
        dict(
            type="scatter",
            mode="lines+markers",
            name="Serious",
            x=indexed,
            y=oil['counts'],
            line=dict(shape="spline", smoothing=2, width=3, color="#F78E09"),
            marker=dict(symbol="diamond-open",size=8,line=dict(width=2,
                                        color='DarkSlateGrey')),
        ),
        dict(
            type="scatter",
            mode="lines+markers",
            name="Fatal",
            x=indexed,
            y=water['counts'],
            line=dict(shape="spline", smoothing=2, width=3, color="#DA240B"),
            marker=dict(symbol="diamond-open",size=8,line=dict(width=2,
                                        color='DarkSlateGrey')),
        ),
    ]
    layout = {
        'autosize': True,
        'automargin': True,
        'title': 'Accidents in different months',
        'legend': {  # Horizontal legens, positioned at the bottom to allow maximum space for the chart
            'orientation': 'h',
            'x': 0,
            'y': 1.01,
            'yanchor': 'bottom',
        },
        'xaxis': {
            'tickvals': indexed,  # Force the tickvals & ticktext just in case
            'ticktext': indexed,
            'tickmode': 'array'
        },
        'transition': {
            'duration': 1000},
        'dragmode': 'select',
    }
    figure = dict(data=data, layout=layout)
    return figure


@app.callback(
    [
        Output("well_text", "children"),
        Output("gasText", "children"),
        Output("oilText", "children"),
        Output("waterText", "children"),
        Output("waterText2", "children"),
    ],
    [Input('year_slider', 'value'),
     Input('severityChecklist', 'value'),
     Input('dayChecklist', 'value'),
     Input('hourSlider', 'value'),
     Input('individual_graph','selectedData'),
     Input('map','selectedData')
     ]
)
def update_text(year,severity, weekdays, time, curve_graph_selected, map_selected):
    hours = [i for i in range(time[0], time[1] + 1)]

    if curve_graph_selected is None:
        months = ['January','February','March','April','May','June','July','August','September','October','November','December']
    else:
        months = [str(mnts["x"]) for mnts in curve_graph_selected["points"]]


    # Create a copy of the dataframe by filtering according to the values passed in.
    # Important to create a copy rather than affect the global object.
    if map_selected is None:
        acc2 = DataFrame(merged[[
            'Accident Severity', 'Location', 'No. of Casualties in Acc.','age_by_decade','Casualty Class']][
                             (merged['Accident Severity'].isin(severity)) &
                             (merged['Day_x'].isin(weekdays)) &
                             (merged['Hour_x'].isin(hours)) &
                             (merged['Accident Year_x'].isin([year])) &
                             (merged['Accident Month_x'].isin(months))
                             ]).reset_index()

    else:
        location = [str(mnts["text"]) for mnts in map_selected["points"]]
        acc2 = DataFrame(merged[[
            'Accident Severity', 'Location', 'No. of Casualties in Acc.', 'age_by_decade', 'Casualty Class']][
                             (merged['Accident Severity'].isin(severity)) &
                             (merged['Day_x'].isin(weekdays)) &
                             (merged['Hour_x'].isin(hours)) &
                             (merged['Accident Year_x'].isin([year])) &
                             (merged['Accident Month_x'].isin(months)) &
                             (merged['Location'].isin(location))
                             ]).reset_index()


    vul_age_grp = acc2.groupby("age_by_decade").size().reset_index(name='counts')
    vul_age_grp_1 = vul_age_grp.sort_values(by='counts', ascending=False).head(1)

    cc = acc2.groupby("Casualty Class").size().reset_index(name='counts')
    ccc = cc.sort_values(by='counts', ascending=False).head(1)

    acc2['cross_street'] = acc2['Location'].str.split(' J/W ',expand=True)[0]
    casualties = acc2["No. of Casualties in Acc."].sum(axis=0)
    most_crashes_on = acc2.groupby("cross_street").size().reset_index(name='counts')
    most_crashes_on_srt = most_crashes_on.sort_values(by='counts', ascending=False)
    most_crashes_on_srt_2 = most_crashes_on_srt.head(1)

    return f'{acc2.count()[0]:,}', f'{int(casualties):,}', most_crashes_on_srt_2["cross_street"],vul_age_grp_1['age_by_decade'],ccc["Casualty Class"]

#Weather tab - KPIs
@app.callback(
    [
        Output("weather_text", "children"),
        Output("temp_text", "children"),
        Output("surf_text", "children"),
        Output("Precip_text", "children"),
        Output("snow_text", "children"),
    ],
    [Input('year_slider_weather', 'value'),
     Input('severityChecklist_weather', 'value'),
     Input('well_statuses_weather','value'),
     ]
)
def update_text_weather(year,severity, months):

    # Create a copy of the dataframe by filtering according to the values passed in.
    # Important to create a copy rather than affect the global object.
    acc2 = DataFrame(acc[[
        'Weather', 'Temp', 'Road Surface','Precipitation','Snowfall Amount']][
                         (acc['Accident Severity'].isin(severity)) &
                         (acc['Accident Year'].isin([year])) &
                         (acc['Accident Month'].isin(months))
                         ]).reset_index()
    
    weather_cond = acc2.groupby("Weather").size().reset_index(name='counts')
    weather_cond1 = weather_cond.sort_values(by='counts', ascending=False).head(1)
    
    avg_temp = round(acc2['Temp'].mean(),1)
    
    road_surf = acc2.groupby("Road Surface").size().reset_index(name='counts')
    road_surf1 = road_surf.sort_values(by='counts', ascending=False).head(1)
    
    avg_prec = round(acc2['Precipitation'].mean(),1)
    avg_snow = round(acc2['Snowfall Amount'].mean(),1)

    return weather_cond1['Weather'], '{} C'.format(avg_temp), road_surf1['Road Surface'].str[5:], '{} mm'.format(avg_prec), '{} cm'.format(avg_snow)




# Run the Dash app
if __name__ == '__main__':
    app.server.run(debug=True, threaded=True)
