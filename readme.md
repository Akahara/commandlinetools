## commandlinetools

A collection of command line tools, for very specific use-cases.

### Tools

- `catimg` - (unix only) display an image in the terminal, without any dependencies (no X server)
- `git-find` - finds all local git repositories and prints uncommited changes
- `git-clone-sparse` - git-clone a single directory from a repo
- `graph-dependencies` - creates a visual graph of a c++ project's include graph (to limit inclusions & optimise build time)
- `drivesync` - git-like service to upload & retrieve files from google drive

## Installation

Simply install the package using python to get (most of) the scripts in your Path, you might need to edit your `PATH` (watch the end of the install logs).
```bash
pip install git+https://github.com/Akahara/commandlinetools
```

For bash scripts you will have to edit your `PATH`.

For `dependency_graph`, you will need [graphviz](https://www.graphviz.org/).

