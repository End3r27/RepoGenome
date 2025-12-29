#!/usr/bin/env python3
"""
Test script for RepoGenome v0.8.0 new functionalities.

Tests:
1. New MCP Tools: get_node, search, dependencies, stats, export
2. New MCP Resources: repogenome://stats, repogenome://nodes/{node_id}
3. Query improvements: pagination, advanced filtering
4. Export formats: CSV, Cypher, PlantUML
"""

import json
from pathlib import Path
from repogenome.mcp.storage import GenomeStorage
from repogenome.mcp.tools import RepoGenomeTools
from repogenome.mcp.resources import RepoGenomeResources
from repogenome.core.schema import RepoGenome

def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_test(name: str, result: dict):
    """Print test result."""
    status = "[PASS]" if "error" not in result else "[FAIL]"
    print(f"\n{status} {name}")
    if "error" in result:
        print(f"   Error: {result['error']}")
    else:
        # Print key information
        if "count" in result:
            print(f"   Count: {result['count']}")
        if "node" in result:
            print(f"   Node ID: {result.get('node', {}).get('id', 'N/A')}")
        if "total_nodes" in result:
            print(f"   Total Nodes: {result['total_nodes']}")
        if "success" in result:
            print(f"   Success: {result['success']}")
        if "output_path" in result:
            print(f"   Output: {result['output_path']}")

def test_mcp_tools():
    """Test new MCP tools."""
    print_section("Testing New MCP Tools")
    
    repo_path = Path(".")
    storage = GenomeStorage(repo_path)
    tools = RepoGenomeTools(storage, str(repo_path))
    
    # Load genome to get a sample node
    genome = storage.load_genome()
    if genome is None:
        print("❌ Cannot load genome. Run 'repogenome generate .' first.")
        return
    
    # Get a sample node ID for testing
    sample_node_id = None
    for node_id in list(genome.nodes.keys())[:10]:
        if genome.nodes[node_id].type == "function":
            sample_node_id = node_id
            break
    
    if not sample_node_id:
        sample_node_id = list(genome.nodes.keys())[0]
    
    print(f"Using sample node: {sample_node_id}")
    
    # Test 1: get_node
    print_test("1. get_node", tools.get_node(sample_node_id))
    
    # Test 2: search
    print_test("2. search (functions)", tools.search(query="function", node_type="function", limit=5))
    print_test("2b. search (Python files)", tools.search(language="Python", file_pattern="*.py", limit=5))
    
    # Test 3: dependencies
    print_test("3. dependencies", tools.dependencies(sample_node_id, direction="both", depth=1))
    
    # Test 4: stats
    stats_result = tools.stats()
    print_test("4. stats", stats_result)
    if "error" not in stats_result:
        print(f"   - Nodes by type: {stats_result.get('nodes_by_type', {})}")
        print(f"   - Total edges: {stats_result.get('total_edges', 0)}")
        print(f"   - Average criticality: {stats_result.get('average_criticality', 0):.2f}")
    
    # Test 5: export (CSV)
    print_test("5. export (CSV)", tools.export(format="csv", output_path="test_export.csv"))
    
    # Test 6: export (Cypher)
    print_test("6. export (Cypher)", tools.export(format="cypher", output_path="test_export.cypher"))
    
    # Test 7: export (PlantUML)
    print_test("7. export (PlantUML)", tools.export(format="plantuml", output_path="test_export.puml"))

def test_mcp_resources():
    """Test new MCP resources."""
    print_section("Testing New MCP Resources")
    
    repo_path = Path(".")
    storage = GenomeStorage(repo_path)
    resources = RepoGenomeResources(storage)
    
    # Test 1: repogenome://stats
    print("\n[TEST] repogenome://stats")
    data, error = resources.get_stats()
    if error:
        print(f"   [FAIL] Error: {error.get('error', 'Unknown error')}")
    else:
        print(f"   [PASS] Success")
        print(f"   - Total nodes: {data.get('total_nodes', 0)}")
        print(f"   - Total edges: {data.get('total_edges', 0)}")
    
    # Test 2: repogenome://nodes/{node_id}
    genome = storage.load_genome()
    if genome:
        sample_node_id = list(genome.nodes.keys())[0]
        print(f"\n[TEST] repogenome://nodes/{sample_node_id}")
        data, error = resources.get_node_resource(sample_node_id)
        if error:
            print(f"   [FAIL] Error: {error.get('error', 'Unknown error')}")
        else:
            print(f"   [PASS] Success")
            print(f"   - Node ID: {data.get('node', {}).get('id', 'N/A')}")
            print(f"   - Incoming edges: {data.get('incoming_count', 0)}")
            print(f"   - Outgoing edges: {data.get('outgoing_count', 0)}")

def test_query_improvements():
    """Test query improvements: pagination and filtering."""
    print_section("Testing Query Improvements")
    
    repo_path = Path(".")
    storage = GenomeStorage(repo_path)
    tools = RepoGenomeTools(storage, str(repo_path))
    
    # Test 1: Pagination
    print("\n[TEST] Query with pagination")
    result1 = tools.query(query="nodes where type='function'", page=1, page_size=10)
    print_test("1. Pagination (page 1, size 10)", result1)
    if "error" not in result1:
        print(f"   - Total count: {result1.get('count', 0)}")
        print(f"   - Page: {result1.get('page', 1)}")
        print(f"   - Total pages: {result1.get('total_pages', 1)}")
        print(f"   - Results on this page: {len(result1.get('results', []))}")
    
    # Test 2: Advanced filtering with AND logic
    print("\n[TEST] Advanced filtering (AND logic)")
    result2 = tools.query(
        query="nodes where type='function'",
        filters={
            "and": [
                {"type": "function"},
                {"language": "Python"}
            ]
        }
    )
    print_test("2. AND filter (function AND Python)", result2)
    
    # Test 3: Advanced filtering with OR logic
    print("\n[TEST] Advanced filtering (OR logic)")
    result3 = tools.query(
        query="nodes",
        filters={
            "or": [
                {"type": "function"},
                {"type": "class"}
            ]
        }
    )
    print_test("3. OR filter (function OR class)", result3)
    
    # Test 4: Query caching (same query twice)
    print("\n[TEST] Query result caching")
    import time
    start1 = time.time()
    result4a = tools.query(query="nodes where type='file'", page=1, page_size=20)
    time1 = time.time() - start1
    
    start2 = time.time()
    result4b = tools.query(query="nodes where type='file'", page=1, page_size=20)
    time2 = time.time() - start2
    
    print(f"   First query: {time1:.4f}s")
    print(f"   Second query (cached): {time2:.4f}s")
    print(f"   Speedup: {time1/time2:.2f}x" if time2 > 0 else "   (caching working)")

def test_export_formats():
    """Test new export formats."""
    print_section("Testing Export Formats")
    
    repo_path = Path(".")
    storage = GenomeStorage(repo_path)
    tools = RepoGenomeTools(storage, str(repo_path))
    
    # Test CSV export
    print_test("1. CSV Export", tools.export(format="csv", output_path="test_genome.csv"))
    csv_path = Path("test_genome.nodes.csv")
    if csv_path.exists():
        print(f"   [PASS] CSV files created: {csv_path} and test_genome.edges.csv")
        print(f"   - Nodes CSV size: {csv_path.stat().st_size} bytes")
    
    # Test Cypher export
    print_test("2. Cypher Export", tools.export(format="cypher", output_path="test_genome.cypher"))
    cypher_path = Path("test_genome.cypher")
    if cypher_path.exists():
        print(f"   [PASS] Cypher file created: {cypher_path}")
        print(f"   - Size: {cypher_path.stat().st_size} bytes")
        # Show first few lines
        with open(cypher_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:5]
            print(f"   - First lines:")
            for line in lines:
                print(f"     {line.strip()}")
    
    # Test PlantUML export
    print_test("3. PlantUML Export", tools.export(format="plantuml", output_path="test_genome.puml"))
    puml_path = Path("test_genome.puml")
    if puml_path.exists():
        print(f"   [PASS] PlantUML file created: {puml_path}")
        print(f"   - Size: {puml_path.stat().st_size} bytes")
        # Show first few lines
        with open(puml_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:5]
            print(f"   - First lines:")
            for line in lines:
                print(f"     {line.strip()}")

def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  RepoGenome v0.8.0 Feature Testing")
    print("=" * 80)
    
    # Check if genome exists
    genome_path = Path("repogenome.json")
    if not genome_path.exists():
        print("\n[ERROR] repogenome.json not found!")
        print("   Please run: repogenome generate .")
        return
    
    # Run tests
    try:
        test_mcp_tools()
        test_mcp_resources()
        test_query_improvements()
        test_export_formats()
        
        print_section("Test Summary")
        print("[SUCCESS] All tests completed!")
        print("\nGenerated test files:")
        test_files = ["test_export.csv", "test_export.cypher", "test_export.puml",
                     "test_genome.csv", "test_genome.cypher", "test_genome.puml"]
        for file in test_files:
            path = Path(file)
            if path.exists() or (file.endswith('.csv') and Path(file.replace('.csv', '.nodes.csv')).exists()):
                print(f"   - {file}")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

