import os
from random import randint

import dash
import flask

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

# Set the global font family
FONT_FAMILY = "Arial"


# Read in data from csv stored on github
# csvLoc = 'accidents2015_V.csv'
csvLoc = 'https://raw.githubusercontent.com/richard-muir/uk-car-accidents/master/accidents2015_V.csv'
acc = read_csv("Attendant_10-17_lat_lon_sample.csv", index_col=0).dropna(how='any', axis=0)
# Remove observations where speed limit is 0 or 10. There's only three and it adds a lot of
#  complexity to the bar chart for no material benefit
acc = acc[~acc['Speed Limit'].isin([0, 10])]
# Create an hour column
acc['Hour'] = acc['Time'].apply(lambda x: int(x.split(':')[0]))

# Set up the Dash instance. Big thanks to @jimmybow for the boilerplate code
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
app.layout = html.Div(
    [
        dcc.Store(id="aggregate_data"),
        # empty Div to trigger javascript file for graph resizing
        html.Div(id="output-clientside"),
        html.Div(
            [
                html.Div(
                    [
                        html.Img(
                            src=app.get_asset_url("london.png"),
                            id="plotly-image",
                            style={
                                "height": "70px",
                                "width": "auto",
                                "margin-bottom": "25px",
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
                            marks={years: years for years in range(2010, 2018)},
                            className="dcc_control",
                            updatemode='mouseup'
                        ),
                        html.Br(),
                        html.P("Filter by Accident Severity:", className="control_label",
                               style={'font-weight': 'bold'}),

                        # dcc.RadioItems(
                        #     id="well_status_selector",
                        #     options=[
                        #         {"label": "All ", "value": "all"},
                        #         {"label": "Active only ", "value": "active"},
                        #         {"label": "Customize ", "value": "custom"},
                        #     ],
                        #     value="active",
                        #     labelStyle={"display": "inline-block"},
                        #     className="dcc_control",
                        # ),
                        dcc.Checklist(  # Checklist for the three different severity values
                            options=[
                                {'label': sev, 'value': sev} for sev in acc['Accident Severity'].unique()
                            ],
                            value=[sev for sev in acc['Accident Severity'].unique()],
                            labelStyle={
                                'display': 'inline-block'
                                # 'paddingRight': 10,
                                # 'paddingLeft': 10,
                                # 'paddingBottom': 5,
                            },
                            className="dcc_control",
                            id="severityChecklist",

                        ),
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
                        # dcc.Dropdown(
                        #     id="well_statuses",
                        #     options=well_status_options,
                        #     multi=True,
                        #     value=list(WELL_STATUSES.keys()),
                        #     className="dcc_control",
                        # ),
                        html.Br(),
                        html.P("Filter by day of Week:", className="control_label", style={'font-weight': 'bold'}),
                        dcc.Checklist(  # Checklist for the dats of week, sorted using the sorting dict created earlier
                            options=[
                                {'label': day[:3], 'value': day} for day in
                                sorted(acc['Day'].unique(), key=lambda k: DAYSORT[k])
                            ],
                            value=[day for day in acc['Day'].unique()],
                            labelStyle={  # Different padding for the checklist elements
                                'display': 'inline-block'
                                # 'paddingRight': 10,
                                # 'paddingLeft': 10,
                                # 'paddingBottom': 5,
                            },
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
                        ),
                        html.P("Upload your data:", className="control_label", style={'font-weight': 'bold'}),
                        dcc.Upload(
                            id='upload-data',
                            children=html.Div([
                                'Drag and Drop or ',
                                html.A('Select Files')
                            ]),
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
                        ),
                    ],
                    className="pretty_container four columns",
                    id="cross-filter-options",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [html.H6(id="well_text"), html.P("No. of Crashes")],
                                    id="wells",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="gasText"), html.P("No. of Casualties")],
                                    id="gas",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="oilText"), html.P("Most Crashes on")],
                                    id="oil",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="waterText"), html.P("Vulnerable Age")],
                                    id="water",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="waterText2"), html.P("Crash Severity")],
                                    id="water2",
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
                    [dcc.Graph(id="pie_graph")],
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
    ],
    id="mainContainer",
    style={"display": "flex", "flex-direction": "column"},
)


## APP INTERACTIVITY THROUGH CALLBACK FUNCTIONS TO UPDATE THE CHARTS ##

# Callback function passes the current value of all three filters into the update functions.
# This on updates the bar.
@app.callback(
    Output(component_id='bar', component_property='figure'),
    [Input(component_id='severityChecklist', component_property='value'),
     Input(component_id='dayChecklist', component_property='value'),
     Input(component_id='hourSlider', component_property='value'),
     Input(component_id='year_slider', component_property='value'),
     ]
)
def updateBarChart(severity, weekdays, time, year):
    # The rangeslider is selects inclusively, but a python list stops before the last number in a range
    hours = [i for i in range(time[0], time[1] + 1)]

    # Create a copy of the dataframe by filtering according to the values passed in.
    # Important to create a copy rather than affect the global object.
    acc2 = DataFrame(acc[[
        'Accident Severity', 'Speed Limit', 'No. of Casualties in Acc.']][
                         (acc['Accident Severity'].isin(severity)) &
                         (acc['Day'].isin(weekdays)) &
                         (acc['Hour'].isin(hours)) &
                         (acc['Accident Year'].isin([year]))
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
               # 'paper_bgcolor': '#F9F9F9',
               # 'plot_bgcolor': '#F9F9F9',
               # 'font': {
               #     'color': '#1a1919'
               # },
               # 'height': "60px",
               'autosize': True,
               'automargin': True,
               'title': 'Accidents by speed limit',
               # 'margin': {  # Set margins to allow maximum space for the chart
               #     'b': 25,
               #     'l': 30,
               #     't': 70,
               #     'r': 0
               # },
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
     ]
)
def updateHeatmap(severity, weekdays, time, year):
    # The rangeslider is selects inclusively, but a python list stops before the last number in a range
    hours = [i for i in range(time[0], time[1] + 1)]
    # Take a copy of the dataframe, filtering it and grouping
    acc2 = DataFrame(acc[[
        'Day', 'Hour', 'No. of Casualties in Acc.']][
                         (acc['Accident Severity'].isin(severity)) &
                         (acc['Day'].isin(weekdays)) &
                         (acc['Hour'].isin(hours)) &
                         (acc['Accident Year'].isin([year]))
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
                   'duration': 1000}
           }}
    return fig


# Feeds the filter outputs into the mapbox
@app.callback(
    Output(component_id='map', component_property='figure'),
    [Input(component_id='severityChecklist', component_property='value'),
     Input(component_id='dayChecklist', component_property='value'),
     Input(component_id='hourSlider', component_property='value'),
     Input(component_id='year_slider', component_property='value'),
     ]
)
def updateMapBox(severity, weekdays, time, year):
    # List of hours again
    hours = [i for i in range(time[0], time[1] + 1)]
    # Filter the dataframe
    acc2 = acc[
        (acc['Accident Severity'].isin(severity)) &
        (acc['Day'].isin(weekdays)) &
        (acc['Hour'].isin(hours)) &
        (acc['Accident Year'].isin([year]))
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
        # 'height': 510,
        # 'height': "300px",
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
        'Accident Severity', 'Location', 'No. of Casualties in Acc.']][
                         (acc['Accident Severity'].isin(severity)) &
                         (acc['Day'].isin(weekdays)) &
                         (acc['Hour'].isin(hours)) &
                         (acc['Accident Year'].isin([year]))
                         ]).reset_index()
    # chosen = [point["customdata"] for point in main_graph_hover["points"]]
    # index, gas, oil, water = produce_individual(chosen[0])
    index = ["Jan", "Feb", "Mar", "Apr", "May"]
    gas = [19, 50, 23, 45, 10]
    oil = [38, 99, 38, 18, 42]

    # if index is None:
    #     annotation = dict(
    #         text="No data available",
    #         x=0.5,
    #         y=0.5,
    #         align="center",
    #         showarrow=False,
    #         xref="paper",
    #         yref="paper",
    #     )
    #     layout_individual["annotations"] = [annotation]
    #     data = []
    # else:
    data = [
        dict(
            type="scatter",
            mode="lines+markers",
            name="Gas Produced (mcf)",
            x=index,
            y=gas,
            line=dict(shape="spline", smoothing=2, width=1, color="#fac1b7"),
            marker=dict(symbol="diamond-open"),
        ),
        dict(
            type="scatter",
            mode="lines+markers",
            name="Oil Produced (bbl)",
            x=index,
            y=oil,
            line=dict(shape="spline", smoothing=2, width=1, color="#a9bb95"),
            marker=dict(symbol="diamond-open"),
        ),
        # dict(
        #     type="scatter",
        #     mode="lines+markers",
        #     name="Water Produced (bbl)",
        #     x=index,
        #     y=water,
        #     line=dict(shape="spline", smoothing=2, width=1, color="#92d8d8"),
        #     marker=dict(symbol="diamond-open"),
        # ),
    ]

    layout = {
        # 'paper_bgcolor': '#F9F9F9',
        # 'plot_bgcolor': '#F9F9F9',
        # 'font': {
        #     'color': '#1a1919'
        # },
        # 'height': "60px",
        'autosize': True,
        'automargin': True,
        'title': 'Accidents in different months',
        # 'margin': {  # Set margins to allow maximum space for the chart
        #     'b': 25,
        #     'l': 30,
        #     't': 70,
        #     'r': 0
        # },
        'legend': {  # Horizontal legens, positioned at the bottom to allow maximum space for the chart
            'orientation': 'h',
            'x': 0,
            'y': 1.01,
            'yanchor': 'bottom',
        },
        'xaxis': {
            'tickvals': index,  # Force the tickvals & ticktext just in case
            'ticktext': index,
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
        Output("waterText2", "children"),
    ],
    [Input('year_slider', 'value'),
     Input('severityChecklist', 'value'),
     Input('dayChecklist', 'value'),
     Input('hourSlider', 'value'),
     ]
)
def update_text(year,severity, weekdays, time):
    hours = [i for i in range(time[0], time[1] + 1)]

    # Create a copy of the dataframe by filtering according to the values passed in.
    # Important to create a copy rather than affect the global object.
    acc2 = DataFrame(acc[[
        'Accident Severity', 'Location', 'No. of Casualties in Acc.']][
                         (acc['Accident Severity'].isin(severity)) &
                         (acc['Day'].isin(weekdays)) &
                         (acc['Hour'].isin(hours)) &
                         (acc['Accident Year'].isin([year]))
                         ]).reset_index()
    casualties = acc2["No. of Casualties in Acc."].sum(axis=0)
    most_crashes_on = acc2.groupby("Location").size().reset_index(name='counts')
    most_crashes_on_srt = most_crashes_on.sort_values(by='counts', ascending=False)
    most_crashes_on_srt_2 = most_crashes_on_srt.head(1)
    crash_sev = acc2.groupby("Accident Severity").size().reset_index(name='counts')
    crash_sev_srt = crash_sev.sort_values(by='counts', ascending=False)
    crash_sev_srt_2 = crash_sev_srt.head(1)
    return f'{acc2.count()[0]:,}', f'{int(casualties):,}', most_crashes_on_srt_2["Location"],crash_sev_srt_2["Accident Severity"]


# Run the Dash app
if __name__ == '__main__':
    app.server.run(debug=True, threaded=True)
