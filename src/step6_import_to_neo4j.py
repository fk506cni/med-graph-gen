
import os
import csv
from neo4j import GraphDatabase

def get_neo4j_driver():
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    return GraphDatabase.driver(uri, auth=(user, password))

def import_nodes(driver, node_file, label, id_field, properties_fields):
    with driver.session() as session:
        with open(node_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            print(f"DEBUG: Headers for {node_file}: {reader.fieldnames}")
            for row in reader:
                # BOM in header
                row = {k.lstrip('\ufeff'): v for k, v in row.items()}
                properties = {field: row[field] for field in properties_fields}
                session.run(f"""
                CREATE (n:{label} {{ {id_field}: $id }})
                SET n += $props
                """, id=row[id_field], props=properties)

def import_edges(driver, edge_file, source_id_field, target_id_field, relation_field, source_node_label, target_node_label, source_node_id_field, target_node_id_field):
    with driver.session() as session:
        with open(edge_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            print(f"DEBUG: Headers for {edge_file}: {reader.fieldnames}")
            for row in reader:
                # BOM in header
                row = {k.lstrip('\ufeff'): v for k, v in row.items()}
                session.run(f"""
                MATCH (a:{source_node_label} {{ {source_node_id_field}: $source_id }})
                MATCH (b:{target_node_label} {{ {target_node_id_field}: $target_id }})
                CREATE (a)-[:`{row[relation_field]}`]->(b)
                """, source_id=row[source_id_field], target_id=row[target_id_field])

def main():
    driver = get_neo4j_driver()

    # Import knowledge graph nodes and edges
    import_nodes(driver, 'output/step5_nodes.csv', 'Node', 'NodeID', ['Label', 'Category'])
    import_edges(driver, 'output/step5_edges.csv', 'SourceID', 'TargetID', 'Relation', 'Node', 'Node', 'NodeID', 'NodeID')

    # Import normalization graph nodes and edges
    import_nodes(driver, 'output/step5_normalization_nodes.csv', 'Term', 'NodeID', ['Label'])
    import_edges(driver, 'output/step5_normalization_edges.csv', 'SourceID', 'TargetID', 'Relation', 'Term', 'Term', 'NodeID', 'NodeID')

    driver.close()
    print("Successfully imported data into Neo4j.")

if __name__ == "__main__":
    main()
