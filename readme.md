## commandlinetools

A collection of command line tools, for very specific use-cases.

### Tools

- `catimg` - display an image in the terminal, without any dependencies (no X server)
- `git-find` - finds all local git repositories and prints uncommited changes
- `graph-dependencies` - creates a visual graph of a c++ project's include graph (to limit inclusions & optimise build time)

## Installation

On linux, simply install the package using python to get (most of) the scripts in your Path.
```bash
pip install git+https://github.com/Akahara/commandlinetools
```

Alternatively, clone the repository and use the files as-is.

For `dependency_graph`, you will need [graphviz](https://www.graphviz.org/).

