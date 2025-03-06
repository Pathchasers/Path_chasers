import pandas as pd
import networkx as nx
import plotly.graph_objs as go
import dash
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
import base64
import io

class EnhancedNexusNetworkVisualizer:
    def __init__(self, systems_csv_path, system_flows_csv_path, table_flows_csv_path, system_images_path=None):
        # Read CSV files
        self.systems_df = pd.read_csv(systems_csv_path)
        self.system_flows_df = pd.read_csv(system_flows_csv_path)
        self.table_flows_df = pd.read_csv(table_flows_csv_path)
        
        # Load system images if path is provided
        self.system_images = {}
        if system_images_path:
            try:
                with open(system_images_path, 'r') as f:
                    image_mapping = pd.read_csv(f)
                    for _, row in image_mapping.iterrows():
                        # Read and encode image
                        with open(row['image_path'], 'rb') as img_file:
                            encoded_image = base64.b64encode(img_file.read()).decode('ascii')
                            self.system_images[row['system_name']] = encoded_image
            except Exception as e:
                print(f"Error loading system images: {e}")

        # Initialize Dash app
        self.app = Dash(__name__)
        
        # Setup layout and callbacks
        self.setup_layout()
        self.setup_callbacks()

    def create_system_network_graph(self):
        # Create NetworkX graph for system-level view
        G = nx.DiGraph()
        
        # Color mapping for different source systems
        color_map = {}
        unique_sources = self.systems_df['source_type'].unique()
        color_palette = [
            '#1F77B4',  # Blue
            '#FF7F0E',  # Orange
            '#2CA02C',  # Green
            '#D62728',  # Red
            '#9467BD',  # Purple
            '#8C564B',  # Brown
            '#E377C2',  # Pink
            '#7F7F7F',  # Gray
        ]
        
        # Assign colors to source types
        for i, source_type in enumerate(unique_sources):
            color_map[source_type] = color_palette[i % len(color_palette)]
        
        # Add systems as nodes with their source types and directions
        for _, system in self.systems_df.iterrows():
            G.add_node(
                system['system_name'], 
                type=system['source_type'],
                source_role=system['source_role'],
                color=color_map.get(system['source_type'], '#1E90FF')
            )
        
        # Add edges with system flow details
        for _, flow in self.system_flows_df.iterrows():
            G.add_edge(
                flow['source_system'], 
                flow['target_system'], 
                weight=flow['flow_weight'],
                direction=flow['flow_direction']
            )
        
        return G, color_map

    def create_system_plotly_graph(self, G, color_map):
        # Compute node positions
        pos = nx.spring_layout(G, k=0.5, iterations=50)
        
        # Prepare edges with arrows
        edge_x, edge_y = [], []
        edge_weights = []
        edge_texts = []
        edge_arrows = []
        for edge in G.edges(data=True):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            
            # Midpoint for arrow placement
            mid_x = (x0 + x1) / 2
            mid_y = (y0 + y1) / 2
            
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            
            weight = edge[2].get('weight', 1)
            edge_weights.append(weight)
            
            # Create detailed edge text
            edge_texts.append(
                f"Source: {edge[0]}<br>" + 
                f"Target: {edge[1]}<br>" + 
                f"Flow Weight: {weight}<br>" + 
                f"Direction: {edge[2].get('direction', 'Unspecified')}"
            )
            
            # Arrow trace
            edge_arrows.append(
                go.Scatter(
                    x=[mid_x], y=[mid_y],
                    mode='markers',
                    marker=dict(
                        symbol='arrow',
                        size=10,
                        color='rgba(100,100,100,0.7)',
                        angle=self._calculate_arrow_angle(pos[edge[0]], pos[edge[1]])
                    ),
                    hoverinfo='none'
                )
            )
        
        # Normalize edge weights for line thickness
        max_weight = max(edge_weights) if edge_weights else 1
        normalized_weights = [2 + (w / max_weight) * 8 for w in edge_weights]
        
        edge_trace = go.Scatter(
            x=edge_x, 
            y=edge_y,
            line=dict(
                width=normalized_weights,
                color='rgba(100,100,100,0.5)'
            ),
            hoverinfo='text',
            text=edge_texts,
            mode='lines'
        )
        
        # Prepare node trace
        node_x, node_y, node_text, node_color, node_size, node_hover = [], [], [], [], [], []
        for node in G.nodes(data=True):
            x, y = pos[node[0]]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node[0])
            
            # Use color from source type
            color = node[1].get('color', '#1E90FF')
            node_color.append(color)
            
            # Adjust node size based on role
            size = 30 if node[1].get('source_role') == 'primary' else 20
            node_size.append(size)
            
            # Prepare hover text with system details
            hover_text = (
                f"System: {node[0]}<br>" +
                f"Type: {node[1].get('type', 'Unknown')}<br>" +
                f"Role: {node[1].get('source_role', 'Unknown')}"
            )
            
            # Add image info to hover if available
            if node[0] in self.system_images:
                hover_text += "<br><img src='data:image/png;base64,{}' width='100' height='100'>".format(
                    self.system_images[node[0]]
                )
            
            node_hover.append(hover_text)
        
        node_trace = go.Scatter(
            x=node_x, 
            y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=node_hover,
            textposition='top center',
            marker=dict(
                showscale=False,
                size=node_size,
                color=node_color,
                line_width=2,
                line_color='white'
            )
        )
        
        # Combine traces, including arrow markers
        all_traces = [edge_trace, node_trace] + edge_arrows
        
        # Create figure
        fig = go.Figure(data=all_traces,
                        layout=go.Layout(
                            title='Enhanced System Network Visualization',
                            showlegend=False,
                            hovermode='closest',
                            margin=dict(b=0,l=0,r=0,t=40),
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                        ))
        
        return fig, color_map

    def _calculate_arrow_angle(self, start_point, end_point):
        """Calculate angle for edge arrow based on line direction."""
        import math
        dx = end_point[0] - start_point[0]
        dy = end_point[1] - start_point[1]
        angle_radians = math.atan2(dy, dx)
        angle_degrees = math.degrees(angle_radians)
        return angle_degrees

    def create_table_network_graph(self, selected_system):
        # Filter table flows for the selected system
        system_flows = self.table_flows_df[
            (self.table_flows_df['source_system'] == selected_system) | 
            (self.table_flows_df['target_system'] == selected_system)
        ]
        
        # Create NetworkX graph
        G = nx.DiGraph()
        
        # Add tables as nodes with system context
        unique_tables = set(system_flows['source_table'].tolist() + 
                            system_flows['target_table'].tolist())
        for table in unique_tables:
            # Find the system this table belongs to
            source_system = system_flows[
                (system_flows['source_table'] == table) & 
                (system_flows['source_system'] == selected_system)
            ]['source_system'].iloc[0] if not system_flows[
                (system_flows['source_table'] == table) & 
                (system_flows['source_system'] == selected_system)
            ].empty else selected_system
            
            G.add_node(
                table, 
                system=source_system
            )
        
        # Add edges with detailed flow information
        for _, flow in system_flows.iterrows():
            G.add_edge(
                flow['source_table'], 
                flow['target_table'], 
                weight=flow['table_flow_weight'],
                transformation=flow.get('transformation', 'Unknown'),
                direction=flow.get('flow_direction', 'Bidirectional')
            )
        
        return G

    def create_table_plotly_graph(self, G, selected_system):
        # Handle empty graph case
        if not G.nodes():
            return go.Figure(layout=go.Layout(
                title=f'No Table Network for {selected_system}',
                annotations=[dict(
                    text='No table connections found',
                    x=0.5, y=0.5,
                    showarrow=False
                )]
            ))

        # Compute node positions
        pos = nx.spring_layout(G, k=0.5, iterations=50)
        
        # Prepare edge trace with arrows
        edge_x, edge_y = [], []
        edge_weights = []
        edge_texts = []
        edge_arrows = []
        for edge in G.edges(data=True):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            
            # Midpoint for arrow placement
            mid_x = (x0 + x1) / 2
            mid_y = (y0 + y1) / 2
            
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            
            weight = edge[2].get('weight', 1)
            edge_weights.append(weight)
            
            # Detailed edge text
            edge_texts.append(
                f"Source Table: {edge[0]}<br>" + 
                f"Target Table: {edge[1]}<br>" + 
                f"Weight: {weight}<br>" + 
                f"Transformation: {edge[2].get('transformation', 'Unknown')}<br>" +
                f"Direction: {edge[2].get('direction', 'Bidirectional')}"
            )
            
            # Arrow trace
            edge_arrows.append(
                go.Scatter(
                    x=[mid_x], y=[mid_y],
                    mode='markers',
                    marker=dict(
                        symbol='arrow',
                        size=10,
                        color='rgba(100,100,100,0.7)',
                        angle=self._calculate_arrow_angle(pos[edge[0]], pos[edge[1]])
                    ),
                    hoverinfo='none'
                )
            )
        
        # Normalize edge weights
        max_weight = max(edge_weights) if edge_weights else 1
        normalized_weights = [2 + (w / max_weight) * 8 for w in edge_weights]
        
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(
                width=normalized_weights,
                color='rgba(100,100,100,0.5)'
            ),
            hoverinfo='text',
            text=edge_texts,
            mode='lines'
        )
        
        # Prepare node trace
        node_x, node_y, node_text, node_color = [], [], [], []
        for node in G.nodes(data=True):
            x, y = pos[node[0]]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node[0])
            
            # Color nodes based on their system
            node_color.append('green' if node[1].get('system') == selected_system else 'purple')
        
        node_trace = go.Scatter(
            x=node_x, 
            y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=node_text,
            textposition='top center',
            marker=dict(
                showscale=False,
                size=15,
                color=node_color,
                line_width=2,
                line_color='white'
            )
        )
        
        # Combine traces, including arrow markers
        all_traces = [edge_trace, node_trace] + edge_arrows
        
        # Create figure
        fig = go.Figure(data=all_traces,
                        layout=go.Layout(
                            title=f'Table Network for {selected_system}',
                            showlegend=False,
                            hovermode='closest',
                            margin=dict(b=0,l=0,r=0,t=40),
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                        ))
        
        return fig

    def setup_layout(self):
        # Create system-level network graph
        G, color_map = self.create_system_network_graph()
        system_fig, _ = self.create_system_plotly_graph(G, color_map)

        # Create a color legend
        color_legend = [
            html.Div([
                html.Div(
                    '',
                    style={
                        'backgroundColor': color,
                        'width': '20px',
                        'height': '20px',
                        'display': 'inline-block',
                        'marginRight': '10px'
                    }
                ),
                html.Span(source_type)
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px'})
            for source_type, color in color_map.items()
        ]

        self.app.layout = html.Div([
            html.H1('Enhanced Nexus Data Warehouse Network Visualization', 
                    style={'textAlign': 'center', 'color': '#1E90FF'}),
            
            # Color Legend
            html.Div(
                color_legend,
                style={
                    'display': 'flex', 
                    'justifyContent': 'center', 
                    'marginBottom': '20px',
                    'gap': '20px'
                }
            ),
            
            # System-level graph
            html.Div([
                html.H2('System-Level View', style={'color': '#4682B4'}),
                dcc.Graph(id='system-network-graph', figure=system_fig)
            ], style={'margin': '20px'}),
            
            # Dropdown for system selection
            html.Div([
                html.Label('Select System for Detailed View:', 
                           style={'fontWeight': 'bold', 'color': '#4682B4'}),
                dcc.Dropdown(
                    id='system-dropdown',
                    options=[{'label': system, 'value': system} 
                             for system in self.systems_df['system_name']],
                    placeholder='Choose a system...',
                    style={'width': '50%'}
                )
            ], style={'margin': '20px'}),
            
            # Table-level graph and details
            html.Div([
                html.H2('Table-Level View', style={'color': '#4682B4'}),
                dcc.Graph(id='table-network-graph'),
                html.Div(id='table-flow-details')
            ], id='table-view-container', style={'margin': '20px'})
        ], style={'fontFamily': 'Arial, sans-serif'})

    def setup_callbacks(self):
        @self.app.callback(
            [Output('table-network-graph', 'figure'),
             Output('table-flow-details', 'children')],
            [Input('system-dropdown', 'value')]
        )
        def update_table_graph(selected_system):
            if not selected_system:
                return go.Figure(), "Select a system to view table details"
            
            # Create table-level network graph
            G = self.create_table_network_graph(selected_system)
            table_fig = self.create_table_plotly_graph(G, selected_system)
            
            # Find table flow details for this system
            flows = self.table_flows_df[
                (self.table_flows_df['source_system'] == selected_system) | 
                (self.table_flows_df['target_system'] == selected_system)
            ]
            
            if flows.empty:
                return table_fig, f"No details available for {selected_system}"
            
            # Create a detailed view of flows with improved styling
            flow_details = [
                html.Div([
                    html.H3(f"Table Flow Details for {selected_system}", 
                            style={'color': '#4682B4'}),
                    html.Table([
                        html.Thead(
                            html.Tr([
                                html.Th('Source Table'), 
                                html.Th('Target Table'), 
                                html.Th('Source System'), 
                                html.Th('Target System'), 
                                html.Th('Flow Weight'), 
                                html.Th('Transformation'),
                                html.Th('Direction')
                            ])
                        ),
                        html.Tbody([
                            html.Tr([
                                html.Td(row['source_table']),
                                html.Td(row['target_table']),
                                html.Td(row['source_system']),
                                html.Td(row['target_system']),
                                html.Td(row['table_flow_weight']),
                                html.Td(row.get('transformation', 'Unknown')),
                                html.Td(row.get('flow_direction', 'Bidirectional'))
                            ]) for _, row in flows.iterrows()
                        ])
                    ], style={
                        'width': '100%', 
                        'borderCollapse': 'collapse', 
                        'marginTop': '10px'
                    })
                ], style={'padding': '15px', 'backgroundColor': '#f0f0f0', 'borderRadius': '5px'})
            ]
            
            return table_fig, flow_details

    def run(self, debug=True, port=8050):
        # Run the app
        self.app.run_server(debug=debug, port=port)

def main():
    """
    Main function to initialize and run the Nexus Network Visualizer.
    Allows customization of CSV file paths and optional system images.
    """
    import argparse
    import os

    # Create argument parser
    parser = argparse.ArgumentParser(
        description='Nexus Data Warehouse Network Visualization Tool'
    )
    
    # Add arguments for CSV file paths
    parser.add_argument(
        '--systems', 
        default='systems.csv', 
        help='Path to systems CSV file'
    )
    parser.add_argument(
        '--system-flows', 
        default='system_flows.csv', 
        help='Path to system flows CSV file'
    )
    parser.add_argument(
        '--table-flows', 
        default='table_flows.csv', 
        help='Path to table flows CSV file'
    )
    parser.add_argument(
        '--system-images', 
        default=None, 
        help='Path to system images mapping CSV file'
    )
    
    # Add port and debug mode arguments
    parser.add_argument(
        '--port', 
        type=int, 
        default=8050, 
        help='Port to run the Dash application'
    )
    parser.add_argument(
        '--debug', 
    