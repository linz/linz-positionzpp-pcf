#!/usr/bin/env python
import argparse
import graphviz
import re
from collections import defaultdict


def parse_pcf_dependency_graph(pcf_path):
    node_pattern = re.compile(r"^(\d{3})\s+(\S+)\s+(\S+)")
    wait_pattern = re.compile(r"WAIT=([0-9 ]+)")
    graph = defaultdict(list)
    labels = {}

    with open(pcf_path, "r") as f:
        for line in f:
            node_match = node_pattern.match(line)
            if node_match:
                node_id = node_match.group(1)
                label = f"{node_match.group(2)} {node_match.group(3)}"
                labels[node_id] = label
                wait_match = wait_pattern.search(line)
                if wait_match:
                    dependencies = [dep.strip() for dep in wait_match.group(1).split()]
                    for dep in dependencies:
                        if dep:
                            graph[node_id].append(dep)
                else:
                    graph[node_id] = []

        return graph, labels


def plot_pcf_dependency_graph(graph, labels, output_png="pcf_dependency_graph.png"):
    dot = graphviz.Digraph(format="png", engine="dot")
    dot.attr(rankdir="TB")

    # Find root nodes (nodes that are not a dependency of any other node)
    all_nodes = set(labels.keys())
    dependent_nodes = set(dep for deps in graph.values() for dep in deps)
    independent_nodes = all_nodes - dependent_nodes

    # Assign colors for nodes
    for node_id, label in labels.items():
        node_attrs = {"shape": "box"}
        if node_id in independent_nodes:
            node_attrs["style"] = "filled"
            node_attrs["fillcolor"] = "pink"
        elif len(graph[node_id]) == 0:
            node_attrs["style"] = "filled"
            node_attrs["fillcolor"] = "lightblue"
        dot.node(node_id, f"{node_id}: {label}", **node_attrs)

    # Add edges for dependencies
    for node_id, deps in graph.items():
        for dep in deps:
            dot.edge(dep, node_id)

    dot.render(filename=output_png, cleanup=True)
    print(f"Dependency graph saved as {output_png}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse and plot PCF dependency graph")
    parser.add_argument("pcf_file", help="Path to the PCF file")
    parser.add_argument(
        "-o",
        "--output",
        default="pcf_dependency_graph.png",
        help="Output PNG file name",
    )
    args = parser.parse_args()

    graph, labels = parse_pcf_dependency_graph(args.pcf_file)
    plot_pcf_dependency_graph(graph, labels, args.output)
