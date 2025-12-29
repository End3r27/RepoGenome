"""
Ragnatela 3D visualization for RepoGenome.

Displays an interactive 3D graph visualization of codebase connections
with main systems (highly connected nodes) as larger spheres.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

try:
    from vispy import app, scene
    from vispy.scene import visuals
    from vispy.scene.cameras import TurntableCamera
except ImportError:
    raise ImportError(
        "vispy is required for ragnatela visualization. Install it with: pip install vispy>=0.14.0"
    )

from repogenome.core.schema import RepoGenome


def find_latest_repogenome(directory: Path) -> Optional[Path]:
    """
    Find the latest repogenome.json file in the directory tree.

    Args:
        directory: Directory to search in

    Returns:
        Path to the latest repogenome.json file, or None if not found
    """
    repogenome_files = list(directory.rglob("repogenome.json"))

    if not repogenome_files:
        return None

    # Sort by modification time, most recent first
    repogenome_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    # Also check metadata.generated_at if available
    latest_file = repogenome_files[0]
    latest_time = latest_file.stat().st_mtime

    for file_path in repogenome_files[1:]:
        try:
            genome = RepoGenome.load(str(file_path))
            if genome.metadata.generated_at:
                file_time = genome.metadata.generated_at.timestamp()
                if file_time > latest_time:
                    latest_file = file_path
                    latest_time = file_time
        except Exception:
            # If we can't load it, fall back to mtime
            pass

    return latest_file


def compute_node_clusters(genome: RepoGenome, node_ids: List[str]) -> Dict[str, int]:
    """
    Compute clusters/communities for nodes using a simple connected component approach.
    
    Args:
        genome: The RepoGenome
        node_ids: List of node IDs to cluster
        
    Returns:
        Dictionary mapping node IDs to cluster IDs
    """
    node_set = set(node_ids)
    clusters = {}
    cluster_id = 0
    
    # Build adjacency list
    adjacency = {node_id: [] for node_id in node_ids}
    for edge in genome.edges:
        if edge.from_ in node_set and edge.to in node_set:
            adjacency[edge.from_].append(edge.to)
            adjacency[edge.to].append(edge.from_)
    
    # Find connected components (simple clustering)
    visited = set()
    for node_id in node_ids:
        if node_id not in visited:
            # BFS to find all connected nodes
            queue = [node_id]
            visited.add(node_id)
            clusters[node_id] = cluster_id
            
            while queue:
                current = queue.pop(0)
                for neighbor in adjacency.get(current, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        clusters[neighbor] = cluster_id
                        queue.append(neighbor)
            
            cluster_id += 1
    
    return clusters


def compute_degree_centrality(genome: RepoGenome) -> Dict[str, int]:
    """
    Compute degree centrality (connection count) for each node.

    Args:
        genome: The RepoGenome to analyze

    Returns:
        Dictionary mapping node IDs to their connection counts
    """
    degree = {node_id: 0 for node_id in genome.nodes.keys()}

    for edge in genome.edges:
        if edge.from_ in degree:
            degree[edge.from_] += 1
        if edge.to in degree:
            degree[edge.to] += 1

    return degree


def compute_3d_layout(
    genome: RepoGenome,
    iterations: int = 50,
    k: Optional[float] = None,
    repulsion_strength: Optional[float] = None,
) -> np.ndarray:
    """
    Compute 3D positions for nodes using force-directed layout.

    Args:
        genome: The RepoGenome to layout
        iterations: Number of layout iterations
        k: Optimal distance between nodes (auto-calculated if None)
        repulsion_strength: Strength of repulsion forces (auto-calculated if None)

    Returns:
        Nx3 numpy array of node positions
    """
    node_ids = list(genome.nodes.keys())
    node_to_index = {node_id: i for i, node_id in enumerate(node_ids)}
    n_nodes = len(node_ids)

    if n_nodes == 0:
        return np.array([])

    # Calculate optimal distance based on number of nodes
    # Use a volume-based calculation: k = (volume / n_nodes)^(1/3)
    if k is None:
        # Estimate volume needed and calculate optimal spacing
        # For 3D, we want nodes spread in a volume proportional to n_nodes
        k = (n_nodes ** (1.0 / 3.0)) * 1.5
        k = max(2.0, min(k, 8.0))  # Clamp between 2 and 8 for better spacing

    # Calculate repulsion strength based on k - make it stronger
    if repulsion_strength is None:
        repulsion_strength = k * k * 100.0  # Increased from 50.0 to 100.0 for stronger repulsion

    # Initialize positions using uniform spherical distribution
    # This ensures nodes start spread out in 3D space
    if n_nodes == 1:
        positions = np.array([[0.0, 0.0, 0.0]])
    else:
        # Use better initial distribution - Fibonacci-like sphere (vectorized for speed)
        radius = k * (n_nodes ** (1.0 / 3.0)) * 3.0  # Larger initial radius
        # Generate points using spherical coordinates for better distribution (vectorized)
        i_array = np.arange(n_nodes, dtype=float)
        theta = np.pi * (3.0 - np.sqrt(5.0)) * i_array  # Golden angle
        y = 1.0 - (2.0 * i_array) / max(n_nodes - 1, 1)  # y goes from 1 to -1
        r = np.sqrt(np.maximum(1.0 - y * y, 0))  # Avoid negative sqrt
        phi = theta
        # Add some randomness
        r_scale = np.random.uniform(0.5, 1.0, n_nodes)
        positions = np.column_stack([
            r_scale * radius * r * np.cos(phi),
            r_scale * radius * y,
            r_scale * radius * r * np.sin(phi),
        ])

    # Build adjacency list
    adjacency = {i: [] for i in range(n_nodes)}
    for edge in genome.edges:
        if edge.from_ in node_to_index and edge.to in node_to_index:
            from_idx = node_to_index[edge.from_]
            to_idx = node_to_index[edge.to]
            adjacency[from_idx].append(to_idx)
            adjacency[to_idx].append(from_idx)

    # Optimize: For large graphs, use approximate repulsion
    use_approximate = n_nodes > 100  # Lower threshold for better performance
    
    # Force-directed layout (Fruchterman-Reingold in 3D)
    # Track convergence for early exit
    prev_positions = positions.copy()
    convergence_threshold = k * 0.01  # Stop if movement is very small
    
    # Progress update interval
    progress_interval = max(1, iterations // 10)  # Update ~10 times
    
    for iteration in range(iterations):
        # Show progress for large graphs
        if n_nodes > 200 and iteration % progress_interval == 0:
            print(f"  Layout iteration {iteration}/{iterations}...")
        forces = np.zeros((n_nodes, 3))

        # Attraction forces along edges
        for edge in genome.edges:
            if edge.from_ in node_to_index and edge.to in node_to_index:
                from_idx = node_to_index[edge.from_]
                to_idx = node_to_index[edge.to]
                delta = positions[to_idx] - positions[from_idx]
                distance = np.linalg.norm(delta)
                if distance > 0:
                    # Spring force: F = (d - k) / k, but limit maximum force
                    force = (distance - k) / max(k, 0.1)
                    force = np.clip(force, -k, k)  # Limit force magnitude
                    force_vec = (delta / distance) * force
                    forces[from_idx] += force_vec
                    forces[to_idx] -= force_vec

        # Repulsion forces - optimized for large graphs
        if use_approximate:
            # For large graphs, use Barnes-Hut style approximation
            # Check repulsion against a sample of nodes, but more intelligently
            if n_nodes > 500:
                # Very large: use center-based repulsion + sample
                center = positions.mean(axis=0)
                for i in range(n_nodes):
                    # Repulsion from center
                    delta_center = positions[i] - center
                    dist_center = np.linalg.norm(delta_center)
                    if dist_center > 0:
                        force_center = repulsion_strength * 0.5 / max(dist_center, 0.1)
                        forces[i] += (delta_center / dist_center) * force_center
                    
                    # Sample-based repulsion
                    sample_size = min(20, n_nodes // 20)
                    sample_indices = np.random.choice(n_nodes, sample_size, replace=False)
                    for j in sample_indices:
                        if i != j:
                            delta = positions[j] - positions[i]
                            distance = np.linalg.norm(delta)
                            if distance > 0:
                                force = repulsion_strength / (distance ** 2 + 0.1)
                                force_vec = delta / distance * force
                                forces[i] -= force_vec * (n_nodes / sample_size)
            else:
                # Medium graphs: use full repulsion but with distance cutoff for speed
                cutoff_dist_sq = (k * 5) ** 2  # Use squared distance to avoid sqrt
                for i in range(n_nodes):
                    for j in range(i + 1, n_nodes):
                        delta = positions[j] - positions[i]
                        distance_sq = np.sum(delta ** 2)
                        if distance_sq > 0 and distance_sq < cutoff_dist_sq:
                            distance = np.sqrt(distance_sq)
                            force = repulsion_strength / (distance_sq + 0.1)
                            force_vec = delta / distance * force
                            forces[i] -= force_vec
                            forces[j] += force_vec
        else:
            # Full repulsion for smaller graphs
            for i in range(n_nodes):
                for j in range(i + 1, n_nodes):
                    delta = positions[j] - positions[i]
                    distance = np.linalg.norm(delta)
                    if distance > 0:
                        # Avoid division by zero and ensure repulsion
                        force = repulsion_strength / (distance ** 2 + 0.1)
                        force_vec = delta / distance * force
                        forces[i] -= force_vec
                        forces[j] += force_vec

        # Update positions with cooling (gradually reduce movement)
        cooling = 1.0 - (iteration / max(iterations, 1)) * 0.7
        step_size = 0.5 * cooling  # Increased from 0.2 to 0.5 for faster convergence
        # Limit maximum step to prevent instability
        max_step = k * 0.5
        force_magnitude = np.linalg.norm(forces, axis=1, keepdims=True)
        force_magnitude = np.where(force_magnitude > max_step, max_step, force_magnitude)
        forces_normalized = forces / (force_magnitude + 1e-10) * force_magnitude
        positions += forces_normalized * step_size

        # Center the graph periodically
        if iteration % 5 == 0:  # Center more frequently
            positions -= positions.mean(axis=0)
        
        # Check for convergence (early exit for faster loading)
        if iteration > 5 and iteration % 5 == 0:  # Check every 5 iterations after initial warmup
            max_movement = np.max(np.linalg.norm(positions - prev_positions, axis=1))
            if max_movement < convergence_threshold:
                print(f"Layout converged early at iteration {iteration}/{iterations}")
                break
            prev_positions = positions.copy()

    # Final centering and scaling
    positions -= positions.mean(axis=0)
    # Scale to reasonable size - ensure 3D distribution
    max_dist = np.max(np.linalg.norm(positions, axis=1))
    if max_dist > 0:
        # Scale to ensure good 3D spread
        target_radius = k * (n_nodes ** (1.0 / 3.0)) * 2.0
        positions = positions / max_dist * target_radius
    else:
        # If everything collapsed, reinitialize with better distribution
        print("Warning: Layout collapsed, reinitializing...")
        radius = k * (n_nodes ** (1.0 / 3.0)) * 2.0
        for i in range(n_nodes):
            theta = np.pi * (3.0 - np.sqrt(5.0)) * i
            y = 1.0 - (2.0 * i) / (n_nodes - 1)
            r = np.sqrt(1.0 - y * y)
            phi = theta
            positions[i] = np.array([
                radius * r * np.cos(phi),
                radius * y,
                radius * r * np.sin(phi),
            ])

    return positions


def compute_node_sizes(degree_centrality: Dict[str, int], base_radius: float = 5.0, scale_factor: float = 15.0) -> Dict[str, float]:
    """
    Compute sphere radii for nodes based on connection count.

    Args:
        degree_centrality: Dictionary mapping node IDs to connection counts
        base_radius: Base radius for all nodes (in pixels/screen units)
        scale_factor: Scaling factor for additional connections (in pixels/screen units)

    Returns:
        Dictionary mapping node IDs to sphere radii
    """
    if not degree_centrality:
        return {}

    max_connections = max(degree_centrality.values())
    min_connections = min(degree_centrality.values())

    node_sizes = {}
    for node_id, connections in degree_centrality.items():
        if max_connections > min_connections:
            normalized = (connections - min_connections) / (max_connections - min_connections)
            # Use exponential scaling for more dramatic size differences
            # This makes highly connected nodes much more visible
            radius = base_radius + (normalized ** 0.7) * scale_factor
        else:
            radius = base_radius
        node_sizes[node_id] = radius

    return node_sizes


def get_node_color(node_type: str, criticality: float = 0.0) -> Tuple[float, float, float, float]:
    """
    Get color for a node based on its type and criticality.

    Args:
        node_type: Type of the node
        criticality: Criticality score (0.0 to 1.0)

    Returns:
        RGBA color tuple
    """
    # Color scheme based on node type
    type_colors = {
        "file": (0.2, 0.6, 1.0, 1.0),  # Blue
        "module": (0.4, 0.8, 1.0, 1.0),  # Light blue
        "function": (0.8, 0.4, 0.2, 1.0),  # Orange
        "class": (0.6, 0.2, 0.8, 1.0),  # Purple
        "test": (0.2, 0.8, 0.4, 1.0),  # Green
        "config": (0.8, 0.8, 0.2, 1.0),  # Yellow
        "resource": (0.8, 0.2, 0.2, 1.0),  # Red
        "concept": (1.0, 0.6, 0.2, 1.0),  # Orange-yellow
    }

    base_color = type_colors.get(node_type.lower(), (0.7, 0.7, 0.7, 1.0))

    # Adjust brightness based on criticality
    brightness = 0.5 + criticality * 0.5
    color = tuple(c * brightness for c in base_color[:3]) + (base_color[3],)

    return color


class RagnatelaCanvas(scene.SceneCanvas):
    """Interactive 3D visualization canvas for RepoGenome."""

    def __init__(self, genome: RepoGenome, min_connections: int = 0):
        # Unfreeze to allow custom attributes (must be before super().__init__)
        # Actually, we'll do it after since SceneCanvas needs to be initialized first
        super().__init__(keys="interactive", size=(1200, 800), show=False, title="Ragnatela - RepoGenome 3D Visualization")
        
        # Unfreeze to allow custom attributes
        self.unfreeze()
        
        self.genome = genome
        self.min_connections = min_connections

        # Filter nodes by minimum connections
        degree_centrality = compute_degree_centrality(genome)
        filtered_nodes = {
            node_id: node
            for node_id, node in genome.nodes.items()
            if degree_centrality.get(node_id, 0) >= min_connections
        }

        if not filtered_nodes:
            raise ValueError(f"No nodes found with {min_connections} or more connections")

        # Create filtered genome for visualization
        self.filtered_node_ids = list(filtered_nodes.keys())
        self.filtered_degree = {k: v for k, v in degree_centrality.items() if k in self.filtered_node_ids}
        
        # Compute clusters
        self.node_clusters = compute_node_clusters(genome, self.filtered_node_ids)
        # Generate colors for clusters
        num_clusters = len(set(self.node_clusters.values())) if self.node_clusters else 0
        if num_clusters > 0:
            import colorsys
            self.cluster_colors = {}
            for i in range(num_clusters):
                hue = i / num_clusters
                rgb = colorsys.hsv_to_rgb(hue, 0.7, 0.9)
                self.cluster_colors[i] = tuple(rgb) + (1.0,)
        else:
            self.cluster_colors = {}

        # Setup scene first so window can be shown
        self.view = self.central_widget.add_view()
        self.view.camera = TurntableCamera(fov=45, distance=10, elevation=30, azimuth=45)
        
        # Show window early with a loading message
        self.show()
        app.process_events()  # Process events to show window

        # Compute layout (this may take time for large graphs)
        n_nodes = len(genome.nodes)
        print(f"Computing 3D layout for {n_nodes} nodes...")
        
        node_ids = list(genome.nodes.keys())
        node_to_index = {node_id: i for i, node_id in enumerate(node_ids)}
        
        # Use fewer iterations for large graphs, but still use force-directed layout
        # Reduced iterations for faster loading
        if n_nodes > 1000:
            print("Using fast approximate layout for large graph...")
            layout_iterations = 10  # Reduced from 15
        elif n_nodes > 500:
            layout_iterations = 15  # Reduced from 25
        elif n_nodes > 200:
            layout_iterations = 25  # Reduced from 50
        else:
            layout_iterations = 30  # Reduced from 50
        
        self.positions = compute_3d_layout(genome, iterations=layout_iterations)
        self.node_indices = {node_id: node_to_index[node_id] for node_id in self.filtered_node_ids}

        # Compute node sizes
        self.node_sizes = compute_node_sizes(self.filtered_degree)
        
        # Build spatial index for faster click detection and frustum culling
        self._build_spatial_index()
        
        # Initialize enhancement attributes
        self.clusters_enabled = False
        self.show_labels = False
        self.node_labels = []
        self.search_query = ""
        self.filtered_node_set = None
        self.search_view = None
        self.search_text_input = None
        self.search_bg = None
        self.search_active = False
        self.selected_node_id = None
        self.minimap_view = None
        self.minimap_nodes = None
        self.minimap_visible = False
        self.animation_timer = None
        self.animation_start_time = None
        self.animation_duration = 0.5
        self.animation_start_camera = None
        self.animation_target_camera = None
        self.edge_data = []
        
        # Hover and selection highlighting
        self.hovered_node_id = None
        self.hover_highlight_visual = None
        self.selection_highlight_visual = None
        
        # Help overlay
        self.help_overlay_visible = False
        self.help_view = None
        
        # Spatial indexing
        self.spatial_grid = None  # Grid-based spatial index
        self.grid_cell_size = None
        
        # Multi-select
        self.selected_nodes = set()  # Set of selected node IDs
        self.multi_select_visuals = []  # Visual indicators for multi-selected nodes
        
        # Path finding
        self.path_visual = None  # Visual for path between nodes
        self.path_start_node = None
        self.path_end_node = None
        
        # Performance monitoring
        self.show_fps = False
        self.fps_view = None
        self.fps_text = None
        self.fps_counter = 0
        self.fps_timer = None
        self.last_fps_time = None
        
        # Color themes
        self.color_theme = 'dark'  # 'dark', 'light', 'high_contrast'
        
        # Control panel
        self.control_panel_visible = False
        self.control_panel_view = None

        # Create visual elements
        print("Creating visualization...")
        self._create_visuals()

        # Setup mouse controls
        self._setup_interaction()
        
        # Update the display
        self.update()

    def _create_visuals(self):
        """Create 3D visual elements (spheres and edges)."""
        # Filter positions and create node visuals
        # First, collect all node data with their sizes
        node_data = []
        
        # Get camera for frustum culling
        camera = self.view.camera
        camera_distance = camera.distance
        
        # Frustum culling: only include nodes that are likely visible
        # Simple check: nodes within reasonable distance from camera
        max_visible_distance = camera_distance * 3.0  # Show nodes up to 3x camera distance
        
        for node_id in self.filtered_node_ids:
            if node_id in self.node_indices:
                idx = self.node_indices[node_id]
                if idx < len(self.positions):
                    node_pos = self.positions[idx]
                    
                    # Frustum culling: check if node is within visible range
                    node_distance = np.linalg.norm(node_pos)
                    if node_distance > max_visible_distance:
                        continue  # Skip nodes that are too far
                    
                    node = self.genome.nodes[node_id]
                    node_size = self.node_sizes.get(node_id, 0.1)
                    # Use cluster color if clustering enabled, otherwise use node type color
                    if self.clusters_enabled and self.node_clusters and node_id in self.node_clusters:
                        cluster_id = self.node_clusters[node_id]
                        node_color = self.cluster_colors.get(cluster_id, get_node_color(node.type.value, node.criticality))
                    else:
                        node_color = get_node_color(node.type.value, node.criticality)
                    
                    node_data.append({
                        'node_id': node_id,
                        'position': node_pos,
                        'size': node_size,
                        'color': node_color,
                    })
        
        if not node_data:
            return
        
        # Sort nodes by size (largest first) for optimized rendering
        node_data.sort(key=lambda x: x['size'], reverse=True)
        n_total = len(node_data)
        print(f"Rendering {n_total} nodes (largest to smallest)...")
        
        # Progressive rendering: show larger nodes first, then add smaller ones
        # For large graphs, render in batches for better perceived performance
        if n_total > 100:
            # Render largest nodes first, then progressively add smaller ones
            batch_size = max(50, n_total // 10)
            num_batches = (n_total + batch_size - 1) // batch_size
            
            # Render first batch (largest nodes) immediately
            first_batch_size = min(batch_size, n_total)
            first_batch = node_data[:first_batch_size]
            
            filtered_positions = [nd['position'] for nd in first_batch]
            filtered_sizes = [nd['size'] for nd in first_batch]
            filtered_colors = [nd['color'] for nd in first_batch]
            self.position_to_node_id = [nd['node_id'] for nd in first_batch]
            
            # Create initial visual with first batch
            node_positions = np.array(filtered_positions)
            node_sizes = np.array(filtered_sizes)
            node_colors = np.array(filtered_colors)
            
            self.node_visual = visuals.Markers()
            self.node_visual.set_data(
                pos=node_positions,
                size=node_sizes,  # Sizes in screen pixels
                face_color=node_colors,
                edge_color="white",
                edge_width=1,
            )
            # Enable perspective scaling (if supported)
            try:
                self.node_visual.symbol = 'o'  # Circle/sphere symbol
            except:
                pass
            self.view.add(self.node_visual)
            self.update()
            app.process_events()
            
            # Store all node data for progressive rendering
            self.all_node_data = node_data
            self.rendered_count = first_batch_size
            self.batch_size = batch_size
            
            # Setup timer for progressive rendering
            self.progressive_timer = app.Timer(interval=0.05, connect=self._add_next_batch, start=True)
        else:
            # For smaller graphs, render all at once
            filtered_positions = [nd['position'] for nd in node_data]
            filtered_sizes = [nd['size'] for nd in node_data]
            filtered_colors = [nd['color'] for nd in node_data]
            self.position_to_node_id = [nd['node_id'] for nd in node_data]

            node_positions = np.array(filtered_positions)
            node_sizes = np.array(filtered_sizes)
            node_colors = np.array(filtered_colors)

            # Create sphere visuals for nodes (already sorted by size)
            self.node_visual = visuals.Markers()
            self.node_visual.set_data(
                pos=node_positions,
                size=node_sizes,  # Sizes in screen pixels
                face_color=node_colors,
                edge_color="white",
                edge_width=1,
            )
            # Enable perspective scaling (if supported)
            try:
                self.node_visual.symbol = 'o'  # Circle/sphere symbol
            except:
                pass
            self.view.add(self.node_visual)
            self.progressive_timer = None
            
            # Create node labels if enabled
            self._create_node_labels(node_data)
        
        # Store node positions for click detection (will be updated progressively)
        self.node_positions_array = node_positions if n_total <= 100 else np.array([nd['position'] for nd in node_data])
        self.node_sizes_array = node_sizes if n_total <= 100 else np.array([nd['size'] for nd in node_data])
        
        # Store base sizes (before distance scaling) for distance-based updates
        self.base_node_sizes = self.node_sizes_array.copy() if n_total <= 100 else np.array([nd['size'] for nd in node_data])

        # Create edge visuals (only between filtered nodes)
        # Store edge data for highlighting
        self.edge_data = []  # List of (from_idx, to_idx, edge) tuples
        edge_positions = []
        edge_colors = []

        for edge in self.genome.edges:
            if edge.from_ in self.filtered_node_ids and edge.to in self.filtered_node_ids:
                if edge.from_ in self.node_indices and edge.to in self.node_indices:
                    from_idx = self.node_indices[edge.from_]
                    to_idx = self.node_indices[edge.to]
                    if from_idx < len(self.positions) and to_idx < len(self.positions):
                        edge_positions.append(self.positions[from_idx])
                        edge_positions.append(self.positions[to_idx])
                        # Light gray edges
                        edge_colors.append((0.5, 0.5, 0.5, 0.3))
                        edge_colors.append((0.5, 0.5, 0.5, 0.3))
                        # Store edge data for highlighting
                        self.edge_data.append((edge.from_, edge.to, edge))

        if edge_positions:
            edge_array = np.array(edge_positions)
            edge_color_array = np.array(edge_colors)
            self.edge_visual = visuals.Line()
            self.edge_visual.set_data(
                pos=edge_array,
                color=edge_color_array,
                width=1,
            )
            self.view.add(self.edge_visual)
            # Store original edge data for highlighting
            self.original_edge_positions = edge_array.copy()
            self.original_edge_colors = edge_color_array.copy()
        else:
            self.edge_visual = None
            self.original_edge_positions = None
            self.original_edge_colors = None

        # Add grid
        grid = visuals.GridLines(color=(0.3, 0.3, 0.3, 0.5))
        self.view.add(grid)
        
        # Create tooltip visuals as 2D overlay
        # Store tooltip data instead of creating visuals immediately
        # We'll create them on-demand when needed
        self.tooltip_text = None
        self.tooltip_bg = None
        self.tooltip_view = None

    def _setup_interaction(self):
        """Setup mouse interaction handlers."""
        # Mouse wheel for zoom
        @self.events.mouse_wheel.connect
        def on_mouse_wheel(event):
            if event.delta[1] > 0:
                self.view.camera.distance *= 0.9
            else:
                self.view.camera.distance *= 1.1
            self._update_node_sizes_for_distance()
            self.update()
        
        # Update sizes when camera changes
        @self.view.camera.events.update.connect
        def on_camera_update(event):
            self._update_node_sizes_for_distance()
            self._update_edge_lod()

        # Mouse click for tooltip and selection
        @self.events.mouse_press.connect
        def on_mouse_press(event):
            if event.button == 1:  # Left click
                # Check for Ctrl key for multi-select
                modifiers = event.modifiers if hasattr(event, 'modifiers') else []
                ctrl_pressed = 'Control' in str(modifiers) if modifiers else False
                
                # Get mouse position in screen coordinates
                screen_pos = event.pos
                
                # Convert to 3D world coordinates using camera
                # We need to find which node is closest to the click ray
                clicked_node_id = self._find_clicked_node(screen_pos)
                
                if clicked_node_id:
                    if ctrl_pressed:
                        # Multi-select mode
                        if clicked_node_id in self.selected_nodes:
                            self.selected_nodes.remove(clicked_node_id)
                        else:
                            self.selected_nodes.add(clicked_node_id)
                        # Update selection indicators
                        self._update_multi_selection_indicators()
                        if hasattr(self, 'control_panel_text'):
                            self._update_control_panel()
                    else:
                        # Single select
                        self.selected_nodes = {clicked_node_id}
                        self.selected_node_id = clicked_node_id
                        self._show_tooltip(clicked_node_id, screen_pos)
                        self._highlight_paths(clicked_node_id)
                        self._update_selection_indicator(clicked_node_id)
                        self._update_multi_selection_indicators()
                        if hasattr(self, 'control_panel_text'):
                            self._update_control_panel()
                else:
                    # Clicked on empty space - clear selection unless Ctrl is held
                    if not ctrl_pressed:
                        self.selected_node_id = None
                        self.selected_nodes.clear()
                        self._hide_tooltip()
                        self._clear_path_highlighting()
                        self._update_selection_indicator(None)
                        self._update_multi_selection_indicators()
                        if hasattr(self, 'control_panel_text'):
                            self._update_control_panel()
                
                self.update()
        
        # Mouse move for hover highlighting
        @self.events.mouse_move.connect
        def on_mouse_move(event):
            # Find node under cursor for hover effect
            screen_pos = event.pos
            hovered_node_id = self._find_clicked_node(screen_pos)
            
            # Update hover highlighting
            if hovered_node_id != getattr(self, 'hovered_node_id', None):
                self.hovered_node_id = hovered_node_id
                self._update_hover_highlighting(hovered_node_id)
        
        # Keyboard shortcuts
        @self.events.key_press.connect
        def on_key_press(event):
            key = event.key.name if hasattr(event.key, 'name') else str(event.key)
            text = event.text if hasattr(event, 'text') else ""
            
            if self.search_active:
                # Handle search input
                if key == 'Backspace':
                    self.search_query = self.search_query[:-1]
                    self._update_search_display()
                    self._apply_filters()
                elif key == 'Escape' or key == 'Enter':
                    self._toggle_search()
                elif text and len(text) == 1 and ord(text) >= 32:  # Printable character
                    self.search_query += text
                    self._update_search_display()
                    self._apply_filters()
                return
            
            if key == 'L' or key == 'l':
                self._toggle_labels()
            elif key == 'S' or key == 's':
                self._toggle_search()
            elif key == 'F' or key == 'f':
                # Focus on selected node (if any)
                if hasattr(self, 'selected_node_id') and self.selected_node_id:
                    self._focus_on_node(self.selected_node_id)
            elif key == 'R' or key == 'r':
                # Reset camera
                camera = self.view.camera
                self.animation_start_camera = {
                    'center': np.array(camera.center),
                    'distance': camera.distance,
                    'elevation': camera.elevation,
                    'azimuth': camera.azimuth,
                }
                self.animation_target_camera = {
                    'center': np.array([0, 0, 0]),
                    'distance': 10.0,
                    'elevation': 30.0,
                    'azimuth': 45.0,
                }
                import time
                self.animation_start_time = time.time()
                if self.animation_timer is None:
                    self.animation_timer = app.Timer(interval=0.016, connect=self._animate_camera, start=True)
                else:
                    self.animation_timer.start()
            elif key == 'M' or key == 'm':
                # Toggle minimap
                self._toggle_minimap()
            elif key == 'C' or key == 'c':
                # Toggle clustering
                self._toggle_clustering()
            elif key == 'H' or key == 'h':
                # Toggle help overlay
                self._toggle_help_overlay()
            elif key == 'Escape':
                # Clear search/filters
                self.search_query = ""
                self.filtered_node_set = None
                self._apply_filters()
    
    def _update_node_sizes_for_distance(self):
        """Update node sizes based on camera distance for perspective scaling."""
        if not hasattr(self, 'node_visual') or not hasattr(self, 'base_node_sizes'):
            return
        
        try:
            camera = self.view.camera
            camera_distance = camera.distance
            
            # Calculate scale factor based on distance
            # Reference distance where scale = 1.0
            reference_distance = 10.0
            scale_factor = reference_distance / max(camera_distance, 0.1)
            # Clamp scale to reasonable range
            scale_factor = max(0.3, min(3.0, scale_factor))
            
            # Apply distance scaling to base sizes
            scaled_sizes = self.base_node_sizes * scale_factor
            
            # Get current visual data
            current_data = self.node_visual._data
            if current_data is None:
                return
            
            # Update sizes
            self.node_visual.set_data(
                pos=current_data['a_position'],
                size=scaled_sizes,
                face_color=current_data['a_fg_color'],
                edge_color="white",
                edge_width=1,
            )
            
            # Update stored sizes array
            self.node_sizes_array = scaled_sizes
        except Exception:
            # Silently fail if update can't be performed
            pass
    
    def _update_edge_lod(self):
        """Update edge level of detail based on camera distance."""
        if not hasattr(self, 'edge_visual') or self.edge_visual is None:
            return
        
        if not hasattr(self, 'original_edge_positions') or self.original_edge_positions is None:
            return
        
        try:
            camera = self.view.camera
            camera_distance = camera.distance
            
            # Simplify edges when zoomed out (reduce opacity and width)
            # When far away, make edges more transparent and thinner
            if camera_distance > 15.0:
                # Far away: very thin, very transparent
                edge_width = 0.5
                edge_alpha = 0.1
            elif camera_distance > 10.0:
                # Medium distance: thin, transparent
                edge_width = 0.7
                edge_alpha = 0.2
            else:
                # Close: normal
                edge_width = 1.0
                edge_alpha = 0.3
            
            # Update edge colors with new alpha
            if hasattr(self, 'original_edge_colors') and self.original_edge_colors is not None:
                new_edge_colors = self.original_edge_colors.copy()
                # Adjust alpha channel
                for i in range(len(new_edge_colors)):
                    if len(new_edge_colors[i]) >= 4:
                        new_edge_colors[i] = tuple(list(new_edge_colors[i][:3]) + [edge_alpha])
                
                self.edge_visual.set_data(
                    pos=self.original_edge_positions,
                    color=new_edge_colors,
                    width=edge_width,
                )
        except Exception:
            # Silently fail if update can't be performed
            pass
    
    
    def _build_spatial_index(self):
        """Build spatial index (grid-based) for faster node lookup."""
        if not hasattr(self, 'positions') or len(self.positions) == 0:
            return
        
        # Calculate grid cell size based on node distribution
        positions = self.positions
        min_pos = positions.min(axis=0)
        max_pos = positions.max(axis=0)
        extent = max_pos - min_pos
        
        # Use grid with approximately 10 cells per dimension
        num_cells = 10
        self.grid_cell_size = extent / num_cells
        self.grid_cell_size = np.maximum(self.grid_cell_size, 0.1)  # Minimum cell size
        
        # Build grid: map cell indices to node indices
        self.spatial_grid = {}
        
        for i, pos in enumerate(positions):
            # Calculate grid cell indices
            cell_idx = ((pos - min_pos) / self.grid_cell_size).astype(int)
            cell_idx = np.clip(cell_idx, 0, num_cells - 1)
            cell_key = tuple(cell_idx)
            
            if cell_key not in self.spatial_grid:
                self.spatial_grid[cell_key] = []
            self.spatial_grid[cell_key].append(i)
    
    def _find_clicked_node(self, screen_pos):
        """Find which node was clicked based on screen position using simplified projection."""
        if not hasattr(self, 'node_positions_array') or len(self.node_positions_array) == 0:
            return None
        
        camera = self.view.camera
        width, height = self.size
        
        # Convert screen coordinates to normalized device coordinates (-1 to 1)
        x_ndc = (screen_pos[0] / width) * 2.0 - 1.0
        y_ndc = 1.0 - (screen_pos[1] / height) * 2.0  # Flip Y axis
        
        # Get camera parameters for simplified projection
        # TurntableCamera uses distance, elevation, azimuth
        camera_distance = camera.distance
        camera_elevation = camera.elevation
        camera_azimuth = camera.azimuth
        
        # Find closest node in screen space using simplified projection
        min_dist_sq = float('inf')
        clicked_index = None
        
        # Calculate camera position and orientation (simplified)
        # For TurntableCamera, the view is centered at origin, camera rotates around
        elevation_rad = np.radians(camera_elevation)
        azimuth_rad = np.radians(camera_azimuth)
        
        # Camera position in world space (simplified turntable model)
        camera_x = camera_distance * np.cos(elevation_rad) * np.sin(azimuth_rad)
        camera_y = camera_distance * np.sin(elevation_rad)
        camera_z = camera_distance * np.cos(elevation_rad) * np.cos(azimuth_rad)
        camera_pos = np.array([camera_x, camera_y, camera_z])
        
        # Approximate view direction (towards origin)
        view_dir = -camera_pos / np.linalg.norm(camera_pos)
        
        # Use spatial grid to narrow down candidate nodes
        candidate_indices = []
        if self.spatial_grid is not None:
            # Find cells near click ray (simplified: check all cells for now)
            # Can be optimized to only check relevant cells
            for cell_nodes in self.spatial_grid.values():
                candidate_indices.extend(cell_nodes)
        else:
            # Fallback: check all nodes
            candidate_indices = list(range(len(self.node_positions_array)))
        
        fov_rad = np.radians(camera.fov)
        
        for i in candidate_indices:
            if i >= len(self.node_positions_array):
                continue
            
            node_pos_3d = self.node_positions_array[i]
            # Calculate vector from camera to node
            to_node = node_pos_3d - camera_pos
            dist_to_node = np.linalg.norm(to_node)
            
            if dist_to_node == 0:
                continue
            
            # Project to view plane (simplified - assumes orthographic-like projection)
            # Use the node's position relative to camera
            # For perspective, we need to project onto the view plane
            # Simplified: use distance from click ray
            
            # Calculate screen position approximation
            # Project node onto view plane (perpendicular to view direction)
            node_to_cam = camera_pos - node_pos_3d
            proj_dist = np.dot(node_to_cam, view_dir)
            
            if proj_dist <= 0:  # Behind camera
                continue
            
            # Calculate perpendicular distance from view ray
            # This gives us an approximation of screen position
            perp_vec = node_to_cam - proj_dist * view_dir
            perp_dist = np.linalg.norm(perp_vec)
            
            # Approximate screen coordinates (very simplified)
            # Use FOV to scale
            fov_rad = np.radians(camera.fov)
            screen_x_approx = (perp_vec[0] / proj_dist) / np.tan(fov_rad / 2)
            screen_y_approx = (perp_vec[1] / proj_dist) / np.tan(fov_rad / 2)
            
            # Calculate distance in screen space
            dist_sq = (screen_x_approx - x_ndc)**2 + (screen_y_approx - y_ndc)**2
            
            # Get node size in screen space (approximate)
            node_radius = self.node_sizes_array[i] * 20 if i < len(self.node_sizes_array) else 10
            # Approximate screen radius based on distance
            screen_radius = (node_radius / proj_dist) * 0.15  # Approximate scaling factor
            
            threshold = screen_radius * screen_radius
            
            if dist_sq < threshold and dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                clicked_index = i
        
        if clicked_index is not None and clicked_index < len(self.position_to_node_id):
            return self.position_to_node_id[clicked_index]
        
        return None
    
    def _show_tooltip(self, node_id, screen_pos):
        """Show tooltip with node information."""
        if node_id not in self.genome.nodes:
            return
        
        node = self.genome.nodes[node_id]
        connections = self.filtered_degree.get(node_id, 0)
        
        # Build tooltip text
        lines = [
            f"Node: {node_id[:50]}",
            f"Type: {node.type.value}",
            f"Connections: {connections}",
        ]
        
        if node.file:
            lines.append(f"File: {node.file[:40]}")
        
        if node.summary:
            lines.append(f"Summary: {node.summary[:40]}")
        
        tooltip_text = "\n".join(lines)
        
        # Position tooltip near click or in corner
        width, height = self.size
        tooltip_x = min(screen_pos[0] + 10, width - 220)
        tooltip_y = height - max(screen_pos[1] + 10, 20)  # Flip Y coordinate for view space (Y=0 at bottom)
        
        # Create tooltip visuals if they don't exist
        if self.tooltip_view is None:
            # Create a 2D overlay view for tooltips
            self.tooltip_view = self.central_widget.add_view(camera='panzoom')
            self.tooltip_view.camera.set_range(x=(0, width), y=(0, height))
            # Make tooltip view not capture mouse events so it doesn't block interactions
            self.tooltip_view.interactive = False
            
            # Create tooltip background
            rect_vertices = np.array([
                [tooltip_x - 5, tooltip_y - 5],
                [tooltip_x + 205, tooltip_y - 5],
                [tooltip_x + 205, tooltip_y + 105],
                [tooltip_x - 5, tooltip_y + 105],
            ])
            self.tooltip_bg = visuals.Polygon(
                pos=rect_vertices,
                color=(0.1, 0.1, 0.1, 0.9),
                parent=self.tooltip_view.scene,
            )
            
            # Create tooltip text
            self.tooltip_text = visuals.Text(
                text="",
                pos=(tooltip_x, tooltip_y),
                color="white",
                font_size=12,
                parent=self.tooltip_view.scene,
            )
        
        # Update tooltip
        self.tooltip_text.text = tooltip_text
        self.tooltip_text.pos = (tooltip_x, tooltip_y)
        self.tooltip_text.visible = True
        
        # Update background rectangle
        num_lines = len(lines)
        bg_height = num_lines * 18 + 10
        bg_width = 210
        # Create or update rectangle vertices
        rect_vertices = np.array([
            [tooltip_x - 5, tooltip_y - 5],
            [tooltip_x - 5 + bg_width, tooltip_y - 5],
            [tooltip_x - 5 + bg_width, tooltip_y - 5 + bg_height],
            [tooltip_x - 5, tooltip_y - 5 + bg_height],
        ])
        
        # Remove old background if it exists
        if self.tooltip_bg is not None:
            try:
                self.tooltip_bg.parent = None
            except:
                pass
        
        # Create new polygon with updated vertices (Polygon doesn't support set_data)
        self.tooltip_bg = visuals.Polygon(
            pos=rect_vertices,
            color=(0.1, 0.1, 0.1, 0.9),
            parent=self.tooltip_view.scene,
        )
        self.tooltip_bg.visible = True
    
    def _hide_tooltip(self):
        """Hide tooltip."""
        if self.tooltip_text is not None:
            self.tooltip_text.visible = False
        if self.tooltip_bg is not None:
            self.tooltip_bg.visible = False
    
    def _create_node_labels(self, node_data):
        """Create text labels for nodes with LOD (Level of Detail)."""
        # Clear existing labels
        for label in self.node_labels:
            try:
                label.parent = None
            except:
                pass
        self.node_labels = []
        
        if not self.show_labels:
            return
        
        # Get camera for distance calculation
        camera = self.view.camera
        camera_distance = camera.distance
        
        # LOD threshold: hide labels beyond this distance
        label_distance_threshold = camera_distance * 1.5
        
        # Create labels for each node (only if within distance threshold)
        for nd in node_data:
            node_id = nd['node_id']
            position = nd['position']
            
            # Calculate distance from camera to node for LOD
            # Simplified distance calculation
            node_distance = np.linalg.norm(position)
            
            # Skip labels that are too far (LOD)
            if node_distance > label_distance_threshold:
                continue
            
            # Truncate long node IDs
            label_text = node_id[:30] + "..." if len(node_id) > 30 else node_id
            
            # Adjust font size based on distance (smaller for distant nodes)
            base_font_size = 10
            distance_factor = max(0.5, min(1.0, label_distance_threshold / max(node_distance, 0.1)))
            font_size = int(base_font_size * distance_factor)
            
            # Create text visual positioned near the node
            label = visuals.Text(
                text=label_text,
                pos=position,
                color="white",
                font_size=font_size,
                parent=self.view.scene,
            )
            # Offset label slightly above node
            label.pos = (position[0], position[1] + 0.3, position[2])
            self.node_labels.append(label)
        
        # Update labels when camera changes (for LOD)
        @self.view.camera.events.update.connect
        def on_camera_update_labels(event):
            if self.show_labels:
                # Recreate labels with updated LOD
                if hasattr(self, 'all_node_data'):
                    current_data = self.all_node_data[:self.rendered_count] if hasattr(self, 'rendered_count') else self.all_node_data
                    self._create_node_labels(current_data)
    
    def _toggle_labels(self):
        """Toggle node labels on/off."""
        self.show_labels = not self.show_labels
        if hasattr(self, 'all_node_data'):
            # Recreate labels with current data
            current_data = self.all_node_data[:self.rendered_count] if hasattr(self, 'rendered_count') else self.all_node_data
            self._create_node_labels(current_data)
        elif hasattr(self, 'node_positions_array'):
            # Recreate from stored data
            node_data = []
            for i, node_id in enumerate(self.position_to_node_id):
                if i < len(self.node_positions_array):
                    node_data.append({
                        'node_id': node_id,
                        'position': self.node_positions_array[i],
                    })
            self._create_node_labels(node_data)
        self.update()
    
    def _toggle_search(self):
        """Toggle search bar visibility."""
        self.search_active = not self.search_active
        if self.search_active:
            self._create_search_ui()
        else:
            self._remove_search_ui()
        self.update()
    
    def _create_search_ui(self):
        """Create search bar UI overlay."""
        if self.search_view is not None:
            return
        
        width, height = self.size
        # Create 2D overlay view for search
        self.search_view = self.central_widget.add_view(camera='panzoom')
        self.search_view.camera.set_range(x=(0, width), y=(0, height))
        # Make search view not capture mouse events except in search area
        self.search_view.interactive = False
        
        # Search background
        self.search_bg = visuals.Rectangle(
            pos=(10, height - 50),
            size=(400, 40),
            color=(0.1, 0.1, 0.1, 0.9),
            parent=self.search_view.scene,
        )
        
        # Search text
        self.search_text_input = visuals.Text(
            text="Search: " + self.search_query + "_",
            pos=(15, height - 35),
            color="white",
            font_size=14,
            parent=self.search_view.scene,
        )
    
    def _update_search_display(self):
        """Update search bar text display."""
        if self.search_text_input is not None:
            width, height = self.size
            self.search_text_input.text = "Search: " + self.search_query + "_"
            self.search_text_input.pos = (15, height - 35)
    
    def _remove_search_ui(self):
        """Remove search bar UI."""
        if self.search_view is not None:
            try:
                self.search_view.parent = None
            except:
                pass
            self.search_view = None
            self.search_text_input = None
            self.search_bg = None
    
    def _apply_filters(self):
        """Apply search/filter to node visualization."""
        if not self.search_query and self.filtered_node_set is None:
            # No filters, show all
            if hasattr(self, 'all_node_data'):
                self._rebuild_visuals_from_data(self.all_node_data[:self.rendered_count] if hasattr(self, 'rendered_count') else self.all_node_data)
            return
        
        # Determine which nodes to show
        visible_node_ids = set()
        
        if self.search_query:
            # Filter by search query
            query_lower = self.search_query.lower()
            for node_id in self.filtered_node_ids:
                node = self.genome.nodes.get(node_id)
                if node:
                    # Search in node ID, file path, type, summary
                    matches = (
                        query_lower in node_id.lower() or
                        (node.file and query_lower in node.file.lower()) or
                        (node.type and query_lower in node.type.value.lower()) or
                        (node.summary and query_lower in node.summary.lower())
                    )
                    if matches:
                        visible_node_ids.add(node_id)
        else:
            # No search, show all filtered nodes
            visible_node_ids = set(self.filtered_node_ids)
        
        # Apply additional filters
        if self.filtered_node_set is not None:
            visible_node_ids = visible_node_ids.intersection(self.filtered_node_set)
        
        # Rebuild visuals with filtered nodes
        filtered_data = []
        if hasattr(self, 'all_node_data'):
            for nd in self.all_node_data:
                if nd['node_id'] in visible_node_ids:
                    filtered_data.append(nd)
        else:
            # Rebuild from current visualization
            for i, node_id in enumerate(self.position_to_node_id):
                if node_id in visible_node_ids and i < len(self.node_positions_array):
                    node = self.genome.nodes.get(node_id)
                    if node:
                        filtered_data.append({
                            'node_id': node_id,
                            'position': self.node_positions_array[i],
                            'size': self.base_node_sizes[i] if i < len(self.base_node_sizes) else self.node_sizes_array[i],
                            'color': get_node_color(node.type.value, node.criticality),
                        })
        
        if filtered_data:
            self._rebuild_visuals_from_data(filtered_data)
        else:
            # Hide all nodes if no matches
            if hasattr(self, 'node_visual'):
                self.node_visual.visible = False
    
    def _rebuild_visuals_from_data(self, node_data):
        """Rebuild node visuals from node data with fade animation."""
        if not node_data:
            # Fade out
            if hasattr(self, 'node_visual'):
                self.node_visual.visible = False
            self.update()
            return
        
        filtered_positions = [nd['position'] for nd in node_data]
        filtered_sizes = [nd['size'] for nd in node_data]
        filtered_colors = [nd['color'] for nd in node_data]
        
        node_positions = np.array(filtered_positions)
        node_sizes = np.array(filtered_sizes)
        node_colors = np.array(filtered_colors)
        
        # Apply distance scaling
        camera = self.view.camera
        camera_distance = camera.distance
        reference_distance = 10.0
        scale_factor = reference_distance / max(camera_distance, 0.1)
        scale_factor = max(0.3, min(3.0, scale_factor))
        scaled_sizes = node_sizes * scale_factor
        
        # Fade in new nodes (start with low opacity)
        fade_colors = []
        for color in node_colors:
            fade_color = list(color[:3]) + [0.3]  # Start with low alpha
            fade_colors.append(fade_color)
        fade_colors = np.array(fade_colors)
        
        # Update visual
        self.node_visual.set_data(
            pos=node_positions,
            size=scaled_sizes,
            face_color=fade_colors,
            edge_color="white",
            edge_width=1,
        )
        self.node_visual.visible = True
        
        # Animate fade in
        import time
        fade_start = time.time()
        fade_duration = 0.3
        
        def fade_in(event=None):
            elapsed = time.time() - fade_start
            progress = min(elapsed / fade_duration, 1.0)
            
            # Fade from 0.3 to full opacity
            alpha = 0.3 + (1.0 - 0.3) * progress
            
            fade_colors = []
            for color in node_colors:
                fade_color = list(color[:3]) + [alpha]
                fade_colors.append(fade_color)
            fade_colors = np.array(fade_colors)
            
            self.node_visual.set_data(
                pos=node_positions,
                size=scaled_sizes,
                face_color=fade_colors,
                edge_color="white",
                edge_width=1,
            )
            self.update()
            
            if progress >= 1.0:
                # Restore full opacity colors
                self.node_visual.set_data(
                    pos=node_positions,
                    size=scaled_sizes,
                    face_color=node_colors,
                    edge_color="white",
                    edge_width=1,
                )
                return False  # Stop timer
        
        fade_timer = app.Timer(interval=0.016, connect=fade_in, start=True, iterations=1)
        
        # Update stored arrays
        self.node_positions_array = node_positions
        self.node_sizes_array = scaled_sizes
        self.position_to_node_id = [nd['node_id'] for nd in node_data]
        
        # Update labels if enabled
        if self.show_labels:
            self._create_node_labels(node_data)
        
        self.update()
    
    def _highlight_paths(self, node_id):
        """Highlight all edges connected to the selected node."""
        if not hasattr(self, 'edge_visual') or self.edge_visual is None:
            return
        
        if not hasattr(self, 'edge_data') or not self.edge_data:
            return
        
        # Get node index
        if node_id not in self.node_indices:
            return
        
        node_idx = self.node_indices[node_id]
        
        # Create new edge colors array
        new_edge_colors = []
        edge_positions = []
        highlighted = False
        
        for edge_from, edge_to, edge in self.edge_data:
            from_idx = self.node_indices.get(edge_from)
            to_idx = self.node_indices.get(edge_to)
            
            if from_idx is None or to_idx is None:
                continue
            
            if from_idx >= len(self.positions) or to_idx >= len(self.positions):
                continue
            
            edge_positions.append(self.positions[from_idx])
            edge_positions.append(self.positions[to_idx])
            
            # Highlight if connected to selected node
            if edge_from == node_id or edge_to == node_id:
                # Bright yellow for highlighted edges
                new_edge_colors.append((1.0, 1.0, 0.0, 0.9))
                new_edge_colors.append((1.0, 1.0, 0.0, 0.9))
                highlighted = True
            else:
                # Keep original colors but slightly dimmed for non-highlighted edges
                edge_idx = len(new_edge_colors) // 2
                if (hasattr(self, 'original_edge_colors') and 
                    self.original_edge_colors is not None and 
                    edge_idx * 2 < len(self.original_edge_colors)):
                    # Use original color but slightly dimmed
                    orig_color = self.original_edge_colors[edge_idx * 2]
                    dimmed_color = tuple(c * 0.5 if i < 3 else c * 0.5 for i, c in enumerate(orig_color))
                    new_edge_colors.append(dimmed_color)
                    new_edge_colors.append(dimmed_color)
                else:
                    # Fallback to slightly dimmed gray
                    new_edge_colors.append((0.25, 0.25, 0.25, 0.15))
                    new_edge_colors.append((0.25, 0.25, 0.25, 0.15))
        
        if edge_positions:
            edge_array = np.array(edge_positions)
            edge_color_array = np.array(new_edge_colors)
            self.edge_visual.set_data(
                pos=edge_array,
                color=edge_color_array,
                width=2 if highlighted else 1,
            )
    
    def _update_hover_highlighting(self, node_id):
        """Update hover highlighting for a node."""
        # Remove old hover highlight
        if self.hover_highlight_visual is not None:
            try:
                self.hover_highlight_visual.parent = None
            except:
                pass
            self.hover_highlight_visual = None
        
        if node_id is None:
            return
        
        # Find node position
        if node_id not in self.position_to_node_id:
            return
        
        idx = self.position_to_node_id.index(node_id)
        if idx >= len(self.node_positions_array):
            return
        
        node_pos = self.node_positions_array[idx]
        node_size = self.node_sizes_array[idx] if idx < len(self.node_sizes_array) else 10
        
        # Create highlight ring around node
        highlight_size = node_size * 1.3
        
        # Create highlight visual (ring/sphere outline)
        self.hover_highlight_visual = visuals.Markers(
            parent=self.view.scene,
        )
        self.hover_highlight_visual.set_data(
            pos=np.array([node_pos]),
            size=highlight_size,
            face_color=(1.0, 1.0, 0.0, 0.3),  # Yellow tint, semi-transparent
            edge_color=(1.0, 1.0, 0.0, 0.8),  # Bright yellow edge
            edge_width=2,
        )
    
    def _update_selection_indicator(self, node_id):
        """Update visual indicator for selected node."""
        # Remove old selection indicator
        if self.selection_highlight_visual is not None:
            try:
                self.selection_highlight_visual.parent = None
            except:
                pass
            self.selection_highlight_visual = None
        
        if node_id is None:
            return
        
        # Find node position
        if node_id not in self.position_to_node_id:
            return
        
        idx = self.position_to_node_id.index(node_id)
        if idx >= len(self.node_positions_array):
            return
        
        node_pos = self.node_positions_array[idx]
        node_size = self.node_sizes_array[idx] if idx < len(self.node_sizes_array) else 10
        
        # Create selection indicator (pulsing ring)
        highlight_size = node_size * 1.5
        
        # Create selection visual with bright cyan color
        self.selection_highlight_visual = visuals.Markers(
            parent=self.view.scene,
        )
        self.selection_highlight_visual.set_data(
            pos=np.array([node_pos]),
            size=highlight_size,
            face_color=(0.0, 1.0, 1.0, 0.4),  # Cyan tint, semi-transparent
            edge_color=(0.0, 1.0, 1.0, 1.0),  # Bright cyan edge
            edge_width=3,
        )
    
    def _update_multi_selection_indicators(self):
        """Update visual indicators for all selected nodes in multi-select mode."""
        # Clear existing multi-select indicators
        if hasattr(self, 'multi_select_visuals'):
            for visual in self.multi_select_visuals:
                try:
                    visual.parent = None
                except:
                    pass
        self.multi_select_visuals = []
        
        if not self.selected_nodes:
            return
        
        # Create indicators for all selected nodes
        positions = []
        sizes = []
        
        for node_id in self.selected_nodes:
            if node_id not in self.position_to_node_id:
                continue
            
            idx = self.position_to_node_id.index(node_id)
            if idx >= len(self.node_positions_array):
                continue
            
            node_pos = self.node_positions_array[idx]
            node_size = self.node_sizes_array[idx] if idx < len(self.node_sizes_array) else 10
            
            positions.append(node_pos)
            sizes.append(node_size * 1.3)  # Slightly larger than node
        
        if positions:
            positions_array = np.array(positions)
            sizes_array = np.array(sizes)
            
            # Create visual for all selected nodes
            multi_visual = visuals.Markers(
                parent=self.view.scene,
            )
            multi_visual.set_data(
                pos=positions_array,
                size=sizes_array,
                face_color=(0.0, 0.8, 1.0, 0.3),  # Light cyan, semi-transparent
                edge_color=(0.0, 0.8, 1.0, 0.8),  # Light cyan edge
                edge_width=2,
            )
            self.multi_select_visuals = [multi_visual]
    
    def _clear_path_highlighting(self):
        """Clear path highlighting and restore original edge colors."""
        if not hasattr(self, 'edge_visual') or self.edge_visual is None:
            return
        
        if (hasattr(self, 'original_edge_colors') and self.original_edge_colors is not None and
            hasattr(self, 'original_edge_positions') and self.original_edge_positions is not None):
            # Restore original colors and positions
            self.edge_visual.set_data(
                pos=self.original_edge_positions,
                color=self.original_edge_colors,
                width=1,
            )
    
    def _focus_on_node(self, node_id):
        """Focus camera on a specific node with animation."""
        if node_id not in self.position_to_node_id:
            return
        
        idx = self.position_to_node_id.index(node_id)
        if idx < len(self.node_positions_array):
            node_pos = self.node_positions_array[idx]
            
            # Store animation start state
            camera = self.view.camera
            self.animation_start_camera = {
                'center': np.array(camera.center),
                'distance': camera.distance,
                'elevation': camera.elevation,
                'azimuth': camera.azimuth,
            }
            
            # Set target state
            self.animation_target_camera = {
                'center': node_pos,
                'distance': 5.0,
                'elevation': 30.0,
                'azimuth': 45.0,
            }
            
            # Start animation
            import time
            self.animation_start_time = time.time()
            
            if self.animation_timer is None:
                self.animation_timer = app.Timer(interval=0.016, connect=self._animate_camera, start=True)
            else:
                self.animation_timer.start()
    
    def _animate_camera(self, event=None):
        """Animate camera movement smoothly."""
        if self.animation_start_camera is None or self.animation_target_camera is None:
            if self.animation_timer:
                self.animation_timer.stop()
            return
        
        import time
        elapsed = time.time() - self.animation_start_time
        progress = min(elapsed / self.animation_duration, 1.0)
        
        # Easing function (ease-in-out)
        if progress < 0.5:
            t = 2 * progress * progress
        else:
            t = 1 - pow(-2 * progress + 2, 2) / 2
        
        # Interpolate camera parameters
        camera = self.view.camera
        start = self.animation_start_camera
        target = self.animation_target_camera
        
        camera.center = start['center'] + (target['center'] - start['center']) * t
        camera.distance = start['distance'] + (target['distance'] - start['distance']) * t
        camera.elevation = start['elevation'] + (target['elevation'] - start['elevation']) * t
        camera.azimuth = start['azimuth'] + (target['azimuth'] - start['azimuth']) * t
        
        self._update_node_sizes_for_distance()
        if self.minimap_visible:
            self._update_minimap()
        self.update()
        
        if progress >= 1.0:
            # Animation complete
            self.animation_timer.stop()
            self.animation_start_camera = None
            self.animation_target_camera = None
    
    def _toggle_minimap(self):
        """Toggle minimap visibility."""
        self.minimap_visible = not self.minimap_visible
        if self.minimap_visible:
            self._create_minimap()
        else:
            self._remove_minimap()
        self.update()
    
    def _create_minimap(self):
        """Create minimap showing 2D projection of graph."""
        if self.minimap_view is not None:
            return
        
        width, height = self.size
        minimap_size = 200
        minimap_x = width - minimap_size - 10
        minimap_y = 10
        
        # Create 2D overlay view for minimap
        self.minimap_view = self.central_widget.add_view(camera='panzoom')
        self.minimap_view.camera.set_range(x=(0, width), y=(0, height))
        # Make minimap view not capture mouse events so it doesn't block interactions
        self.minimap_view.interactive = False
        
        # Minimap background
        minimap_bg = visuals.Rectangle(
            pos=(minimap_x, minimap_y),
            size=(minimap_size, minimap_size),
            color=(0.1, 0.1, 0.1, 0.8),
            parent=self.minimap_view.scene,
        )
        
        # Project 3D positions to 2D for minimap
        # Use top-down view (X-Z plane)
        if hasattr(self, 'node_positions_array') and len(self.node_positions_array) > 0:
            # Get bounds
            positions_2d = self.node_positions_array[:, [0, 2]]  # X and Z coordinates
            min_x, min_z = positions_2d.min(axis=0)
            max_x, max_z = positions_2d.max(axis=0)
            
            # Normalize to minimap coordinates
            range_x = max_x - min_x if max_x != min_x else 1.0
            range_z = max_z - min_z if max_z != min_z else 1.0
            
            # Scale to fit minimap
            scale = min((minimap_size - 20) / range_x, (minimap_size - 20) / range_z)
            
            minimap_positions = []
            for pos_3d in self.node_positions_array:
                x_norm = (pos_3d[0] - min_x) * scale + 10
                z_norm = (pos_3d[2] - min_z) * scale + 10
                minimap_positions.append([minimap_x + x_norm, minimap_y + z_norm])
            
            # Create minimap nodes
            minimap_pos_array = np.array(minimap_positions)
            self.minimap_nodes = visuals.Markers()
            self.minimap_nodes.set_data(
                pos=minimap_pos_array,
                size=3,
                face_color="white",
                edge_color="gray",
                edge_width=0.5,
                parent=self.minimap_view.scene,
            )
    
    def _update_minimap(self):
        """Update minimap viewport indicator."""
        # Could add viewport rectangle showing current camera view
        pass
    
    def _remove_minimap(self):
        """Remove minimap."""
        if self.minimap_view is not None:
            try:
                self.minimap_view.parent = None
            except:
                pass
            self.minimap_view = None
            self.minimap_nodes = None
    
    def _toggle_clustering(self):
        """Toggle node clustering visualization."""
        self.clusters_enabled = not self.clusters_enabled
        # Rebuild visuals with new color scheme
        if hasattr(self, 'all_node_data'):
            self._create_visuals()
        self.update()
    
    def _toggle_help_overlay(self):
        """Toggle help overlay showing keyboard shortcuts."""
        self.help_overlay_visible = not self.help_overlay_visible
        if self.help_overlay_visible:
            self._create_help_overlay()
        else:
            self._remove_help_overlay()
        self.update()
    
    def _create_help_overlay(self):
        """Create help overlay with keyboard shortcuts."""
        if self.help_view is not None:
            return
        
        width, height = self.size
        
        # Create 2D overlay view for help
        self.help_view = self.central_widget.add_view(camera='panzoom')
        self.help_view.camera.set_range(x=(0, width), y=(0, height))
        self.help_view.interactive = False
        
        # Help background
        help_bg = visuals.Rectangle(
            pos=(width - 320, 10),
            size=(310, 400),
            color=(0.1, 0.1, 0.1, 0.95),
            parent=self.help_view.scene,
        )
        
        # Help text with shortcuts
        help_text = """Keyboard Shortcuts:

L - Toggle node labels
S - Toggle search
F - Focus on selected node
R - Reset camera
M - Toggle minimap
C - Toggle clustering
H - Toggle this help

Mouse Controls:
- Drag: Rotate camera
- Wheel: Zoom in/out
- Click: Select node

Press H to close"""
        
        self.help_text_visual = visuals.Text(
            text=help_text,
            pos=(width - 315, 20),
            color="white",
            font_size=12,
            parent=self.help_view.scene,
        )
    
    def _remove_help_overlay(self):
        """Remove help overlay."""
        if self.help_view is not None:
            try:
                self.help_view.parent = None
            except:
                pass
            self.help_view = None
            self.help_text_visual = None
    
    def _add_next_batch(self, event=None):
        """Add next batch of nodes for progressive rendering."""
        if not hasattr(self, 'all_node_data') or self.rendered_count >= len(self.all_node_data):
            # All nodes rendered, stop timer
            if hasattr(self, 'progressive_timer') and self.progressive_timer:
                self.progressive_timer.stop()
            return
        
        # Get next batch
        end_count = min(self.rendered_count + self.batch_size, len(self.all_node_data))
        nodes_to_render = self.all_node_data[:end_count]
        
        if not nodes_to_render or end_count == self.rendered_count:
            if hasattr(self, 'progressive_timer') and self.progressive_timer:
                self.progressive_timer.stop()
            return
        
        # Rebuild visual with all nodes rendered so far
        filtered_positions = [nd['position'] for nd in nodes_to_render]
        filtered_sizes = [nd['size'] for nd in nodes_to_render]
        filtered_colors = [nd['color'] for nd in nodes_to_render]
        
        node_positions = np.array(filtered_positions)
        node_sizes = np.array(filtered_sizes)
        node_colors = np.array(filtered_colors)
        
        # Update visual with all nodes rendered so far
        # Apply distance scaling
        camera = self.view.camera
        camera_distance = camera.distance
        reference_distance = 10.0
        scale_factor = reference_distance / max(camera_distance, 0.1)
        scale_factor = max(0.3, min(3.0, scale_factor))
        scaled_sizes = node_sizes * scale_factor
        
        self.node_visual.set_data(
            pos=node_positions,
            size=scaled_sizes,
            face_color=node_colors,
            edge_color="white",
            edge_width=1,
        )
        
        # Update position arrays for click detection
        self.position_to_node_id = [nd['node_id'] for nd in nodes_to_render]
        self.node_positions_array = node_positions
        self.node_sizes_array = scaled_sizes
        # Update base sizes
        if not hasattr(self, 'base_node_sizes'):
            self.base_node_sizes = node_sizes.copy()
        else:
            # Extend base sizes array
            self.base_node_sizes = np.array([nd['size'] for nd in self.all_node_data[:end_count]])
        
        # Update labels if enabled
        if self.show_labels:
            self._create_node_labels(nodes_to_render)
        
        self.rendered_count = end_count
        
        # Update display
        self.update()
        app.process_events()
        
        # Stop timer if all nodes are rendered
        if self.rendered_count >= len(self.all_node_data):
            if hasattr(self, 'progressive_timer') and self.progressive_timer:
                self.progressive_timer.stop()
            print(f"Finished rendering all {len(self.all_node_data)} nodes.")

    def run(self):
        """Run the visualization."""
        app.run()


def visualize_ragnatela(
    genome_path: Optional[Path] = None,
    search_directory: Optional[Path] = None,
    min_connections: int = 0,
) -> None:
    """
    Visualize a RepoGenome file in 3D.

    Args:
        genome_path: Direct path to repogenome.json file
        search_directory: Directory to search for latest repogenome.json
        min_connections: Minimum number of connections to show a node
    """
    # Determine which file to load
    if genome_path:
        if not genome_path.exists():
            raise FileNotFoundError(f"Genome file not found: {genome_path}")
        file_path = genome_path
    elif search_directory:
        file_path = find_latest_repogenome(search_directory)
        if not file_path:
            raise FileNotFoundError(
                f"No repogenome.json file found in {search_directory} or subdirectories"
            )
    else:
        # Default to current directory
        current_dir = Path.cwd()
        file_path = find_latest_repogenome(current_dir)
        if not file_path:
            raise FileNotFoundError(
                f"No repogenome.json file found in {current_dir} or subdirectories"
            )

    # Load genome
    genome = RepoGenome.load(str(file_path))

    if not genome.nodes:
        raise ValueError("Genome file contains no nodes")

    # Create and run visualization
    canvas = RagnatelaCanvas(genome, min_connections=min_connections)
    canvas.run()

