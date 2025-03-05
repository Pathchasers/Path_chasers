import pandas as pd
import networkx as nx
import plotly.graph_objs as go
import dash
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
import base64
import io

class NexusNetworkVisualizer:
    def __init__(self, system_csv_path, flow_csv_path, system_images_path=None):
        # Read CSV files
        self.systems_df = pd.read_csv(system_csv_path)
        self.flows_df = pd.read_csv(flow_csv_path)
        
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
        
        # Add systems as nodes
        for _, system in self.systems_df.iterrows():
            G.add_node(
                system['system_name'], 
                type=system['system_type']
            )
        
        # Compute edge weights from flows
        system_flows = self.flows_df.groupby(['source_system', 'target_system'])['weight'].sum().reset_index()
        
        # Add edges with weights
        for _, flow in system_flows.iterrows():
            G.add_edge(
                flow['source_system'], 
                flow['target_system'], 
                weight=flow['weight']
            )
        
        return G

    def create_system_plotly_graph(self, G):
        # Compute node positions
        pos = nx.spring_layout(G, k=0.5, iterations=50)
        
        # Prepare edges
        edge_x, edge_y = [], []
        edge_weights = []
        edge_texts = []
        for edge in G.edges(data=True):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            weight = edge[2].get('weight', 1)
            edge_weights.append(weight)
            edge_texts.append(f"Flow Weight: {weight}")
        
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
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node)
            
            # Determine color and size based on system type
            if node == 'Nexus':
                color = 'red'
                size = 30
            else:
                color = 'blue'
                size = 20
            node_color.append(color)
            node_size.append(size)
            
            # Prepare hover text with additional system details
            system_info = self.systems_df[self.systems_df['system_name'] == node]
            hover_text = f"System: {node}<br>Type: {system_info['system_type'].values[0]}"
            
            # Add image info to hover if available
            if node in self.system_images:
                hover_text += "<br><img src='data:image/png;base64,{}' width='100' height='100'>".format(
                    self.system_images[node]
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
        
        # Create figure
        fig = go.Figure(data=[edge_trace, node_trace],
                        layout=go.Layout(
                            title='Nexus Data Warehouse - System Network',
                            showlegend=False,
                            hovermode='closest',
                            margin=dict(b=0,l=0,r=0,t=40),
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                        ))
        
        return fig

    def create_table_network_graph(self, selected_system):
        # Filter flows for the selected system
        system_flows = self.flows_df[
            (self.flows_df['source_system'] == selected_system) | 
            (self.flows_df['target_system'] == selected_system)
        ]
        
        # Create NetworkX graph
        G = nx.DiGraph()
        
        # Add tables as nodes
        unique_tables = set(system_flows['source_table'].tolist() + 
                            system_flows['target_table'].tolist())
        for table in unique_tables:
            G.add_node(table)
        
        # Add edges with flow details
        for _, flow in system_flows.iterrows():
            G.add_edge(
                flow['source_table'], 
                flow['target_table'], 
                weight=flow['weight'],
                transformation=flow.get('transformation', 'Unknown')
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
        
        # Prepare edge trace
        edge_x, edge_y = [], []
        edge_weights = []
        edge_texts = []
        for edge in G.edges(data=True):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            weight = edge[2].get('weight', 1)
            edge_weights.append(weight)
            edge_texts.append(
                f"Source: {edge[0]}<br>" + 
                f"Target: {edge[1]}<br>" + 
                f"Weight: {weight}<br>" + 
                f"Transformation: {edge[2].get('transformation', 'Unknown')}"
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
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node)
            # Color nodes based on whether they are source or target
            node_color.append('green' if node in self.flows_df['source_table'].values else 'purple')
        
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
        
        # Create figure
        fig = go.Figure(data=[edge_trace, node_trace],
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
        G = self.create_system_network_graph()
        system_fig = self.create_system_plotly_graph(G)

        self.app.layout = html.Div([
            html.H1('Nexus Data Warehouse Network Visualization', 
                    style={'textAlign': 'center', 'color': '#1E90FF'}),
            
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
            
            # Find flow details for this system
            flows = self.flows_df[
                (self.flows_df['source_system'] == selected_system) | 
                (self.flows_df['target_system'] == selected_system)
            ]
            
            if flows.empty:
                return table_fig, f"No details available for {selected_system}"
            
            # Create a detailed view of flows with improved styling
            flow_details = [
                html.Div([
                    html.H3(f"Flow Details for {selected_system}", 
                            style={'color': '#4682B4'}),
                    html.Table([
                        html.Thead(
                            html.Tr([
                                html.Th('Source Table'), 
                                html.Th('Target Table'), 
                                html.Th('Source System'), 
                                html.Th('Target System'), 
                                html.Th('Weight'), 
                                html.Th('Transformation')
                            ])
                        ),
                        html.Tbody([
                            html.Tr([
                                html.Td(row['source_table']),
                                html.Td(row['target_table']),
                                html.Td(row['source_system']),
                                html.Td(row['target_system']),
                                html.Td(row['weight']),
                                html.Td(row.get('transformation', 'Unknown'))
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

    def run(self, debug=True):
        # Run the app
        self.app.run_server(debug=debug)

def main():
    # Paths to your CSV files
    system_csv_path = 'systems.csv'
    flow_csv_path = 'data_flows.csv'
    
    # Optional: Path to system images mapping
    system_images_path = 'system_images.csv'

    # Create and run the visualizer
    visualizer = NexusNetworkVisualizer(
        system_csv_path, 
        flow_csv_path, 
        system_images_path
    )
    visualizer.run()

if __name__ == '__main__':
    main()
```

To make this more interactive and support images, I've added several enhancements:

1. **System Images Support**:
   - Added an optional parameter to load system images
   - Created a method to read and encode system images
   - Included images in hover tooltips for system nodes

2. **Improved Interactivity**:
   - Replaced system click with a dropdown for system selection
   - Enhanced hover information for both system and table network graphs
   - Added more detailed styling and layout

Sample CSV files you'll need:

systems.csv:
```
system_name,system_type
CRM System,source
ERP System,source
Nexus,target
```

data