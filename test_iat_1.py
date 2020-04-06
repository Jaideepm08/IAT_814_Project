import os
from random import randint
import sys
import dash
import flask
import pandas as pd
import plotly.graph_objs as go


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


# Read in data from csv stored on github
acc = read_csv("/Users/jaideepmishra/Downloads/IAT_814_Project/Attendant_10-17_lat_lon_sample.csv", index_col=0).dropna(how='any', axis=0)
casualty = read_csv("/Users/jaideepmishra/PycharmProjects/Dash/casualty_df.csv", index_col=0).dropna(how='any', axis=0)
# acc = read_csv("data/Attendant_10-17_lat_lon_sample.csv", index_col=0).dropna(how='any', axis=0)
# casualty = read_csv("data/casualty_df.csv", index_col=0).dropna(how='any', axis=0)
casualty['Hour'] = casualty['Time'].apply(lambda x: int(x.split(':')[0]))

# Remove observations where speed limit is 0 or 10. There's only three and it adds a lot of
#  complexity to the bar chart for no material benefit
acc = acc[~acc['Speed Limit'].isin([0, 10])]
# Create an hour column
acc['Hour'] = acc['Time'].apply(lambda x: int(x.split(':')[0]))
acc['Temp'] = acc['Temp'].round(0)# Set up the Dash instance. Big thanks to @jimmybow for the boilerplate code
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
app.title = 'My Title'
# Main layout container
app.layout = html.Div([
        dcc.Store(id="aggregate_data"),
        # empty Div to trigger javascript file for graph resizing
        html.Div(id="output-clientside"),
        html.Div(
            [
                html.Div(
                    [
                        dcc.Upload(
                            id='upload-data',
                            children=html.Div([html.A('Custom Dataset')]),
                            style={
                                'width': '90%',
                                'height': '60px',
                                'lineHeight': '60px',
                                'borderWidth': '1px',
                                'borderStyle': 'dashed',
                                'borderRadius': '5px',
                                'textAlign': 'center',
                                'margin': '10px'
                            },
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
                            href="https://plot.ly/dash/pricing/",
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
                            "Filter by incident date (or select range in histogram):",
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
                            labelStyle={'display': 'inline-block'},       
                            className="check",
                            id="severityChecklist",

                        ),
                    html.Br(),
                     dcc.Graph(id='year-graph',
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
                            [dcc.Graph(id="map")],
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
                    [dcc.Graph(id="pie_graph"
                               )],
                    className="pretty_container seven columns",
                ),
                html.Div(
                    [dcc.Graph(id="individual_graph")],
                    className="pretty_container five columns",
                ),
            ],
            className="row flex-display",
        ),
        html.Div(
            [
                html.Div(
                    [dcc.Graph(id="heatmap")],
                    className="pretty_container seven columns",
                ),
                html.Div(
                    [dcc.Graph(id="bar")],
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
                            labelStyle={'display': 'inline-block'},
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
                        ),
                        dcc.Graph(id='temp_graph') 
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
                            [dcc.Graph()],
                            id="weatherGraphContainer",
                            className="pretty_container",
                        ),
                    ],
                    id="right-column_weather",
                    className="eight columns",
                ),
            ],
            className="row flex-display",
        )
               
               
               
               
               ]),
       dcc.Tab(label='Road Conditions', children=[]),
       dcc.Tab(label='Vehicle Details', children=[]),
    ]),
        
    ],
    id="mainContainer",
    style={"display": "flex", "flex-direction": "column"},
)

#This callback takes input from year-graph and gives output to year_slider
@app.callback(
    Output('year_slider', 'value'),
    [Input('year-graph', 'clickData')])
def display_click_data(clickData):
    if clickData is None:
        return 2012
    return clickData['points'][0]['x']

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
               Input('heatmap','selectedData'),
               ])
def make_scatter(year, severity, weekdays, time, curve_graph_selected, heat_map_selected):
    if curve_graph_selected is None:
        months = ['January','February','March','April','May','June','July','August','September','October','November','December']
    else:
        months = [str(mnts["x"]) for mnts in curve_graph_selected["points"]]

    #print("selected data",check)
    # The rangeslider is selects inclusively, but a python list stops before the last number in a range
    hours = [i for i in range(time[0], time[1] + 1)]
    # Take a copy of the dataframe, filtering it and grouping
    acc2 = DataFrame(acc[[
        'Day', 'Hour', 'No. of Casualties in Acc.']][
                         (acc['Accident Severity'].isin(severity)) &
                         (acc['Day'].isin(weekdays)) &
                         (acc['Hour'].isin(hours)) &
                         (acc['Accident Year'].isin([year])) &
                         (acc['Accident Month'].isin(months))
                         ].groupby(['Day', 'Hour']).sum()).reset_index()

    # Apply text after grouping
    def heatmapText(row):
        return 'Day : {}<br>Time : {:02d}:00<br>Number of casualties: {}'.format(row['Day'],
                                                                                 row['Hour'],
                                                                                 row['No. of Casualties in Acc.'])

    # acc2['text'] = acc2.apply(heatmapText, axis=1)

    # Pre-sort a list of days to feed into the heatmap
    days = sorted(acc2['Day'].unique(), key=lambda k: DAYSORT[k])



    # Create the z-values and text in a nested list format to match the shape of the heatmap
    # z = []
    # text = []
    # for d in days:
    #     row = acc2['No. of Casualties in Acc.'][acc2['Day'] == d].values.tolist()
    #     t = acc2['text'][acc2['Day'] == d].values.tolist()
    #     z.append(row)
    #     text.append(t)
    # print(hours)

    figure = {
        'data': [
            go.Scatter(
                x=acc2['Hour'],#.apply(lambda w: "{}{}".format(w,':00')),
                y=sorted(acc2['Day'], key=lambda k: DAYSORT[k]),
                #text=df[df['continent'] == i]['country'],
                mode='markers',
                marker_symbol='square',
                opacity=0.8,
                marker={
                    'size': 34,
                    'line':{'width':2,'color':'DarkSlateGrey'},
                    'cmax': max(acc2['No. of Casualties in Acc.']),
                    'cmin':min(acc2['No. of Casualties in Acc.']),
                    #'line': {'width': 0},
                    'color': acc2['No. of Casualties in Acc.'],
                    'colorscale': 'blues',
                    'colorbar' :{'title':"Count"},
                },

            )
        ],

        'layout': {
                        'clickmode': 'event+select',
                        'title':'Accidents with respect to Day and Time',
                        'xaxis':{'title': 'Hours','dtick' :2,'range':[0,24]},
                        'yaxis':{'title': 'Days'},
                        #'margin':{'l': 40, 'b': 40, 't': 80, 'r': 10},
                        'legend':{'orientation': 'h','x': 0, 'y': 1,'yanchor': 'bottom'},
                        'transition': {'duration': 500}
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
     Input('individual_graph','selectedData')
     ]
)
def updateBarChart(severity, weekdays, time, year, curve_graph_selected):
    if curve_graph_selected is None:
        months = ['January','February','March','April','May','June','July','August','September','October','November','December']
    else:
        months = [str(mnts["x"]) for mnts in curve_graph_selected["points"]]
    # The rangeslider is selects inclusively, but a python list stops before the last number in a range
    hours = [i for i in range(time[0], time[1] + 1)]

    # Create a copy of the dataframe by filtering according to the values passed in.
    # Important to create a copy rather than affect the global object.
    acc2 = DataFrame(acc[[
        'Accident Severity', 'Speed Limit', 'No. of Casualties in Acc.']][
                         (acc['Accident Severity'].isin(severity)) &
                         (acc['Day'].isin(weekdays)) &
                         (acc['Hour'].isin(hours)) &
                         (acc['Accident Year'].isin([year])) &
                         (acc['Accident Month'].isin(months))
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
                   'duration': 100}
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
     ]
)
def updateHeatmap(severity, weekdays, time, year,curve_graph_selected):
    if curve_graph_selected is None:
        months = ['January','February','March','April','May','June','July','August','September','October','November','December']
    else:
        months = [str(mnts["x"]) for mnts in curve_graph_selected["points"]]

    #print("selected data",check)
    # The rangeslider is selects inclusively, but a python list stops before the last number in a range
    hours = [i for i in range(time[0], time[1] + 1)]
    # Take a copy of the dataframe, filtering it and grouping
    acc2 = DataFrame(acc[[
        'Day', 'Hour', 'No. of Casualties in Acc.']][
                         (acc['Accident Severity'].isin(severity)) &
                         (acc['Day'].isin(weekdays)) &
                         (acc['Hour'].isin(hours)) &
                         (acc['Accident Year'].isin([year])) &
                         (acc['Accident Month'].isin(months))
                         ].groupby(['Day', 'Hour']).sum()).reset_index()

    # Apply text after grouping
    def heatmapText(row):
        return 'Day : {}<br>Time : {:02d}:00<br>Number of casualties: {}'.format(row['Day'],
                                                                                 row['Hour'],
                                                                                 row['No. of Casualties in Acc.'])

    acc2['text'] = acc2.apply(heatmapText, axis=1)

    # Pre-sort a list of days to feed into the heatmap
    days = sorted(acc2['Day'].unique(), key=lambda k: DAYSORT[k])

    # Create the z-values and text in a nested list format to match the shape of the heatmap
    z = []
    text = []
    for d in days:
        row = acc2['No. of Casualties in Acc.'][acc2['Day'] == d].values.tolist()
        t = acc2['text'][acc2['Day'] == d].values.tolist()
        z.append(row)
        text.append(t)

    # Plotly standard 'Electric' colourscale is great, but the maximum value is white, as is the
    #  colour for missing values. I set the maximum to the penultimate maximum value,
    #  then spread out the other. Plotly colourscales here: https://github.com/plotly/plotly.py/blob/master/plotly/colors.py

    Electric = [
        [0, 'rgb(0,0,0)'], [0.25, 'rgb(30,0,100)'],
        [0.55, 'rgb(120,0,100)'], [0.8, 'rgb(160,90,0)'],
        [1, 'rgb(230,200,0)']
    ]

    # Heatmap trace
    traces = [{
        'type': 'heatmap',
        'x': hours,
        'y': days,
        'z': z,
        'text': text,
        'hoverinfo': 'text',
        'colorscale': 'Viridis',
    }]

    fig = {'data': traces,
           'layout': {
               'autosize': True,
               'automargin': True,
               'title': 'Accidents by time and day',
               'xaxis': {
                   'ticktext': hours,  # for the tickvals and ticktext with one for each hour
                   'tickvals': hours,
                   'tickmode': 'array',
               },
               'transition': {
                   'duration': 500}
           }}
    return fig


# Feeds the filter outputs into the mapbox
@app.callback(
    Output(component_id='map', component_property='figure'),
    [Input(component_id='severityChecklist', component_property='value'),
     Input(component_id='dayChecklist', component_property='value'),
     Input(component_id='hourSlider', component_property='value'),
     Input(component_id='year_slider', component_property='value'),
     Input('individual_graph','selectedData'),
     ]
)
def updateMapBox(severity, weekdays, time, year, curve_graph_selected):
    if curve_graph_selected is None:
        months = ['January','February','March','April','May','June','July','August','September','October','November','December']
    else:
        months = [str(mnts["x"]) for mnts in curve_graph_selected["points"]]
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
               Input('individual_graph','selectedData')])
def make_year_graph(severity,weekdays,time,curve_graph_selected):
    hours = [i for i in range(time[0], time[1] + 1)]
    if curve_graph_selected is None:
        months = ['January','February','March','April','May','June','July','August','September','October','November','December']
    else:
        months = [str(mnts["x"]) for mnts in curve_graph_selected["points"]]
    hours = [i for i in range(time[0], time[1] + 1)]
    acc2 = DataFrame(acc[[
        'Accident Severity', 'Accident Year']][
                         (acc['Accident Severity'].isin(severity))&
                         (acc['Day'].isin(weekdays)) &
                         (acc['Hour'].isin(hours)) &
                         (acc['Accident Month'].isin(months))   
                         ]).reset_index()
    figure={
                            'data': [
                                {'x': acc2.groupby(["Accident Year"]).size().reset_index(name='counts')['Accident Year'], 
                                 'y': acc2.groupby(["Accident Year"]).size().reset_index(name='counts')['counts'], 
                                 'type': 'bar',
                                 'marker': {'color': '#99cfe0','width': 0.1}
                                 }                                
                            ],
                            'layout': {
                                'title': 'Filter by Years',
                                'clickmode': 'event+select',
                                'xaxis':{'title': 'Year','dtick' :1},
                                'bargap':0.5,
                                'height':300
                            }
                        }
    return figure

#make temp_graph
@app.callback(Output("temp_graph", "figure"),
              [Input('severityChecklist_weather', 'value')])
def make_temp_graph(severity):
    acc2 = DataFrame(acc[[
        'Accident Severity', 'Temp']][
                         (acc['Accident Severity'].isin(severity))   
                         ]).reset_index()
    figure={
                            'data': [
                                {'x': acc2.groupby(["Temp"]).size().reset_index(name='counts')['Temp'], 
                                 'y': acc2.groupby(["Temp"]).size().reset_index(name='counts')['counts'], 
                                 'type': 'line',
                                 #'marker': {'color': '#99cfe0','width': 0.1}
                                 }                                
                            ],
                            'layout': {
                                'title': 'Filter by Temperature',
                                'clickmode': 'event+select',
                                'xaxis':{'title': 'Temperature(C)','dtick' :5,'range':[-5,40]},
                                'bargap':0.5,
                                'height':300
                            }
                        }
    return figure
# Main graph -> individual graph
@app.callback(Output("individual_graph", "figure"),
              [Input('year_slider', 'value'),
               Input('severityChecklist', 'value'),
               Input('dayChecklist', 'value'),
               Input('hourSlider', 'value'),
               ])
def make_individual_figure(year, severity, weekdays, time):

    hours = [i for i in range(time[0], time[1] + 1)]
    # Create a copy of the dataframe by filtering according to the values passed in.
    # Important to create a copy rather than affect the global object.
    acc2 = DataFrame(acc[[
        'Accident Severity', 'Location', 'No. of Casualties in Acc.','Accident Month']][
                         (acc['Accident Severity'].isin(severity)) &
                         (acc['Day'].isin(weekdays)) &
                         (acc['Hour'].isin(hours)) &
                         (acc['Accident Year'].isin([year]))
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
            'duration': 1000}
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
     ]
)
def update_text(year,severity, weekdays, time, curve_graph_selected):
    if curve_graph_selected is None:
        months = ['January','February','March','April','May','June','July','August','September','October','November','December']
    else:
        months = [str(mnts["x"]) for mnts in curve_graph_selected["points"]]
    hours = [i for i in range(time[0], time[1] + 1)]

    # Create a copy of the dataframe by filtering according to the values passed in.
    # Important to create a copy rather than affect the global object.
    acc2 = DataFrame(acc[[
        'Accident Severity', 'Location', 'No. of Casualties in Acc.']][
                         (acc['Accident Severity'].isin(severity)) &
                         (acc['Day'].isin(weekdays)) &
                         (acc['Hour'].isin(hours)) &
                         (acc['Accident Year'].isin([year])) &
                         (acc['Accident Month'].isin(months))
                         ]).reset_index()
    cas = DataFrame(casualty[[
        'Casualty Severity', 'Casualty Age (Banded)','Casualty Class']][
                         (casualty['Casualty Severity'].isin(severity)) &
                         (casualty['Day'].isin(weekdays)) &
                         (casualty['Hour'].isin(hours)) &
                         (casualty['Accident Year'].isin([year])) &
                         (casualty['Accident Month'].isin(months))
                         ]).reset_index()

    vul_age_grp = cas.groupby("Casualty Age (Banded)").size().reset_index(name='counts')
    vul_age_grp_1 = vul_age_grp.sort_values(by='counts', ascending=False).head(1)

    cc = cas.groupby("Casualty Class").size().reset_index(name='counts')
    ccc = cc.sort_values(by='counts', ascending=False).head(1)

    acc2['cross_street'] = acc2['Location'].str.split(' J/W ',expand=True)[0]
    casualties = acc2["No. of Casualties in Acc."].sum(axis=0)
    most_crashes_on = acc2.groupby("cross_street").size().reset_index(name='counts')
    most_crashes_on_srt = most_crashes_on.sort_values(by='counts', ascending=False)
    most_crashes_on_srt_2 = most_crashes_on_srt.head(1)

    return f'{acc2.count()[0]:,}', f'{int(casualties):,}', most_crashes_on_srt_2["cross_street"],vul_age_grp_1['Casualty Age (Banded)'],ccc["Casualty Class"]

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
     Input('individual_graph','selectedData'),
     ]
)
def update_text_weather(year,severity, curve_graph_selected):
    if curve_graph_selected is None:
        months = ['January','February','March','April','May','June','July','August','September','October','November','December']
    else:
        months = [str(mnts["x"]) for mnts in curve_graph_selected["points"]]

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
