#!/bin/env python

"""
Creates a graph of the include-tree of a C/C++ project.
The point is to reduce unwanted dependencies in header files, that way one does
not have to recompile the whole project when making changes to a single header
file.

You will to install graphviz to use this tool -> https://graphviz.org/

Usage:
graph-dependencies <project root directory> <graph output file> [options...]

I highly encourage you to create a .bash or .bat file per-project, for example,
I use this .bat file in one of my projects:
python graph-dependencies PebbleEngine\src out^
	-e wtypes,bitset,algorithm,sstream,cmath,filesystem,fstream^
	-e iostream,string_view,string,unordered_map,stdexcept,vector^
	-e stdint,memory,tchar,exception,utility,array,locale,codecvt^
	-e stack,cassert,functional,queue,unordered_set,concepts^
	-i scene1,math

"""

import os
import re
import argparse
import codecs
from graphviz import Digraph

INCLUDE_REGEX = re.compile('#include\s+["<"](.*)[">]')
VALID_HEADERS = [['.h', '.hpp'], 'red']
VALID_SOURCES = [['.c', '.cc', '.cpp'], 'blue']
VALID_EXTENSIONS = VALID_HEADERS[0] + VALID_SOURCES[0]

### Set from command line arguments globally because it's less of a bother
external_selection_is_optin = False
graph_headers_only = True
notable_externals = set()
excluded_internals = set()
###
    
def is_acceptable_external(file):
    file_in_notable_externals = file in notable_externals or get_file_name(file) in notable_externals
    return file_in_notable_externals == external_selection_is_optin
    
def is_acceptable_internal(file):
    return (file not in excluded_internals) and (get_file_name(file) not in excluded_internals) and (not graph_headers_only or get_file_extension(file) in VALID_HEADERS[0])

def get_file_from_path(path):
    return os.path.basename(path)

def get_file_name(file):
    end = file.rfind('.')
    return file[:end] if end != -1 else file

def get_file_extension(path):
    return path[path.rfind('.'):]

def collect_files(path):
    files = []
    for entry in os.scandir(path):
        if entry.is_dir():
            files += collect_files(entry.path)
        elif get_file_extension(entry.path) in VALID_EXTENSIONS:
            files.append(entry.path)
    return files

def find_inclusions(path):
    f = codecs.open(path, 'r', "utf-8", "ignore")
    code = f.read()
    f.close()
    return set(get_file_from_path(include) for include in INCLUDE_REGEX.findall(code))

def create_graph(folder):
    # collect nodes
    all_internal_files = collect_files(folder)
    internal_files = [f for f in all_internal_files if is_acceptable_internal(get_file_from_path(f))]
    inclusions = {get_file_from_path(f): find_inclusions(f) for f in internal_files}
    all_internal_files = list(map(get_file_from_path, all_internal_files))
    internal_files = list(map(get_file_from_path, internal_files))
    
    def is_valid_inclusion(n):
        return n in internal_files if n in all_internal_files else is_acceptable_external(n)
    
    neighbours = {f: list(filter(is_valid_inclusion, inclusions[f])) for f in inclusions}
    external_files = set(sum(neighbours.values(), [])) - set(map(get_file_from_path, all_internal_files))
    
    # Create graph
    graph = Digraph()
    for path in internal_files:
        node = get_file_name(path)
        ext = get_file_extension(path)
        outgoing_links_colors = VALID_HEADERS[1] if ext in VALID_HEADERS[0] else VALID_SOURCES[1]
        graph.node(node, color="black")
        for neighbor in map(get_file_name, neighbours[path]):
            if neighbor == node:
                continue
            graph.edge(node, neighbor, color=outgoing_links_colors)
    for node in external_files:
        graph.node(get_file_name(node), color="orange")
        
    return graph


def main():
    global external_selection_is_optin, graph_headers_only, notable_externals, excluded_internals

    parser = argparse.ArgumentParser()
    parser.add_argument('folder', help='Path to the folder to scan')
    parser.add_argument('output', help='Path of the output file without the extension')
    parser.add_argument('-f', '--format', help='Format of the output',\
        default='pdf', choices=['bmp', 'gif', 'jpg', 'png', 'pdf', 'svg'])
    parser.add_argument('--opt-in-externals', action='store_true',\
        help='Only include external files given with -e (by default include externals that are *not* given with -e)')
    parser.add_argument('-e', '--external', action='append',\
        help='Set a file as a notable external, may be given multiple times or separated with comas. If extension is not provided, any file with the same name will match. See --opt-in-externals')
    parser.add_argument('--include-source-files', action='store_true',\
        help='Include source files in the graph (.c, .cpp...)')
    parser.add_argument('-i', '--exclude-internal', action='append',\
        help='Exclude a specific internal file from the graph, if no extension is given, any file with the same name will match. May be given multiple times or separated by comas')
    
    args = parser.parse_args()
    
    external_selection_is_optin = args.opt_in_externals
    graph_headers_only = not args.include_source_files
    notable_externals = [n for l in (args.external or []) for n in l.split(',')]
    excluded_internals = [n for l in (args.exclude_internal or []) for n in l.split(',')]
    
    graph = create_graph(args.folder)
    graph.format = args.format
    graph.render(args.output, cleanup=True)


if __name__ == '__main__':
    main()