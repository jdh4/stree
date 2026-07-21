# stree
Python script that wraps Slurm sshare to help explain queue times

## Requirements

- Python 3.7+
- treelib 1.7.1+
- blessed (optional)

Do not use treelib 1.7.0 or you will encounter errors when printing trees.

Different packages needed for dev.

```
conda create --name tree-env python=3.10 treelib blessed pytest ruff mypy pre-commit -c conda-forge
```

If need to get cluster name to distinguish different sshare outputs:

```
scontrol show config | grep '^ClusterName'
```
