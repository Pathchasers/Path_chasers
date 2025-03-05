import pandas as pd
import networkx as nx
import plotly.graph_objs as go
import dash
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State

class NexusNetworkVisualizer:
    def __init__(self, system_csv_path, flow_csv_path):
        # Read CSV files
        self.systems_df = pd.read_csv(system_csv_path)
        self.flows_df = pd.read_csv(flow_csv_path)

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
        for edge in G.edges(data=True):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            edge_weights.append(edge[2].get('weight', 1))
        
        # Normalize edge weights for line thickness
        max_weight = max(edge_weights) if edge_weights else 1
        
        edge_trace = go.Scatter(
            x=edge_x, 
            y=edge_y,
            line=dict(
                width=5,  # Fixed width or use a normalized approach
                color='rgba(100,100,100,0.5)'
            ),
            hoverinfo='none',
            mode='lines'
        )
        
        # Prepare node trace
        node_x, node_y, node_text, node_color = [], [], [], []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node)
            node_color.append('blue' if node == 'Nexus' else 'green')
        
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
            edge_weights.append(edge[2].get('weight', 1))
            edge_texts.append(f"Transformation: {edge[2].get('transformation', 'Unknown')}")
        
        # Normalize edge weights
        max_weight = max(edge_weights) if edge_weights else 1
        
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(
                width=5,  # Fixed width or use normalized approach
                color='rgba(100,100,100,0.5)'
            ),
            hoverinfo='text',
            text=edge_texts,
            mode='lines'
        )
        
        # Prepare node trace
        node_x, node_y, node_text = [], [], []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node)
        
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
                color='purple',
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
            html.H1('Nexus Data Warehouse Network Visualization'),
            
            # System-level graph
            html.Div([
                html.H2('System-Level View'),
                dcc.Graph(id='system-network-graph', figure=system_fig)
            ]),
            
            # Table-level graph (initially hidden)
            html.Div([
                html.H2('Table-Level View'),
                dcc.Graph(id='table-network-graph'),
                html.Div(id='table-flow-details')
            ], id='table-view-container', style={'display': 'none'}),
            
            # Hidden storage for selected system
            dcc.Store(id='selected-system-store')
        ])

    def setup_callbacks(self):
        @self.app.callback(
            [Output('selected-system-store', 'data'),
             Output('table-view-container', 'style')],
            [Input('system-network-graph', 'clickData')]
        )
        def on_system_click(clickData):
            if not clickData:
                return None, {'display': 'none'}
            
            # Get the clicked system name
            selected_system = clickData['points'][0]['text']
            
            return selected_system, {'display': 'block'}

        @self.app.callback(
            [Output('table-network-graph', 'figure'),
             Output('table-flow-details', 'children')],
            [Input('selected-system-store', 'data')]
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
            
            # Create a detailed view of flows
            flow_details = [
                html.Div([
                    html.Strong(f"Flow: {row['source_table']} → {row['target_table']}"),
                    html.P(f"System: {row['source_system']} → {row['target_system']}"),
                    html.P(f"Weight: {row['weight']}"),
                    html.P(f"Transformation: {row.get('transformation', 'Unknown')}")
                ]) for _, row in flows.iterrows()
            ]
            
            return table_fig, flow_details

    def run(self, debug=True):
        # Run the app
        self.app.run_server(debug=debug)

def main():
    # Paths to your CSV files
    system_csv_path = 'systems.csv'
    flow_csv_path = 'data_flows.csv'

    # Create and run the visualizer
    visualizer = NexusNetworkVisualizer(system_csv_path, flow_csv_path)
    visualizer.run()

if __name__ == '__main__':
    main()