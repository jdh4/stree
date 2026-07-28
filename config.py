# number of characters for output
WIDTH = 80

# number of digits of precision to show
FAIRSHARE_DIGITS = 4

USAGE_DIGITS = 0
SHARES_DIGITS = 0
SHARES_PREC = 0

# if this path is found for a given node then ignore root
# otherwise level 1 of the tree is considered where slurm does the most important stuff
# this is needed for computing department shares against a total
# if this path is found then ignore root and start at end of path
# is a pattern needed to differentiate different clusters?
SKIP_ROOT_ACCOUNTS = ("total", "pli", "ailab")

# if set then will be displayed at bottom of verbose output
MORE_INFO_URL = "https://researchcomputing.princeton.edu/support/knowledge-base/job-priority"

# specify the factors instead of using auto-detect (options are ...)
FACTORS = ("SITE", "AGE", "FAIRSHARE", "JOBSIZE", "QOS")

# how many master tables to output if multiple accounts were found in verbose mode
REPEAT_ALL_TABLES = False

SHOW_ZERO_USAGE = False

# show or ignore the weights paragraph
INCLUDE_JOB_PRIORITY_POST_AMBLE = True

# instead of bold for Shares column could also only show account and shares
# how to tell about CS, LSI, PNI, MATH, cloud computing?
# how to specify the priority needed for a job to run per cluster?
# CLI option to show users with zero usage
# how can a user only see the data for one account of their many (lowercase a)?
