# number of digits of precision to show
FAIRSHARE_DIGITS = 4

# if this path is found for a given node then ignore root
# otherwise level 1 of the tree is considered where slurm does the most important stuff
# this is needed for computing department shares against a total
# if this path is found then ignore root and start at end of path
# is a pattern needed to differentiate different clusters?
SPECIAL_SUBTREES = (("root", "total"), ("root", "pli"))
SKIP_ROOT_ACCOUNTS = [("root", "total"), ("root", "pli")]
IGNORE_ROOT = ["root/total", "root>pli"]
#ROOT_OVERRIDES = []


# how to color lines that are both users and accounts such as pli?


IGNORE_TREE_TOTAL = False

# if set then will be displayed at bottom of verbose output
MORE_INFO_URL = "https://researchcomputing.princeton.edu/support/knowledge-base/job-priority"

SPECIAL_DEPTS = ["shs", "subotnik"]

STANDARD_NODE = "total (--)"

OTHER_NODE = "pli (--)"

# specify the factors instead of using auto-detect
FACTORS = ["SITE", "AGE", "FAIRSHARE", "JOBSIZE", "QOS"]

# how many tables to output if multiple accounts were found in verbose mode
REPEAT_ALL_TABLES = False

SHOW_ZERO_USAGE = False
