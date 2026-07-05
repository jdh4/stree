"""There are three children under root:
       1. root
       2. pli
       3. total

   Note that andlinger has users at level 5 in the tree. This is believed to be
   true for other accounts somewhere in the three.

   Leading spaces in each line of the output of sshare are used to determine
   the level of the tree.

   from longwait import ShareTree
   mytree = ShareTree(); mytree.get_raw_data(); mytree.parse()

   print(mytree.tree["shs (--)"].data)

   for i, c in enumerate(mytree.tree.children("pni (--)")):
       print(i+1, c.data)
"""


import os
import argparse
import subprocess
from treelib import Tree
from typing import Optional
from typing import Union
from typing import List
import config as c
try:
    from blessed import Terminal
    blessed_is_available = True
except ModuleNotFoundError:
    blessed_is_available = False


class TreeNode:

    """
    Represents a single node (Account or User) in the sshare hierarchy.
    """
    def __init__(self,
                 account,
                 user,
                 raw_shares,
                 norm_shares,
                 raw_usage,
                 effectv_usage,
                 fair_share,
                 level_fs,
                 level):
        self.account = account
        self.user = user
        self.raw_shares = raw_shares
        self.norm_shares = norm_shares
        self.raw_usage = raw_usage
        self.effectv_usage = effectv_usage
        self.fair_share = fair_share
        self.level_fs = level_fs
        self.level = level

    def __str__(self):
        return (f"level: {self.level}, account: {self.account}, user: {self.user}, raw shares: {self.raw_shares}, "
                f"effective usage: {self.effectv_usage}, fs: {self.fair_share}, lfs: {self.level_fs}")


class ShareTree:

    def __init__(self) -> None:
        self.tree = Tree()
        self.num_accounts = 0


    def get_raw_data(self, text: Optional[str] = None) -> None:
        """Get the data from either sacct or a string to build the tree. The
           string makes it possible to test the code."""
        if text:
            self.lines = text.splitlines()
        else:
            fmt = "Account,User,RawShares,NormShares,RawUsage,EffectvUsage,FairShare,LevelFS"
            cmd = f"sshare -a -l -n -o {fmt}"
            output = subprocess.run(cmd,
                                    stdout=subprocess.PIPE,
                                    encoding="utf8",
                                    check=True,
                                    text=True,
                                    shell=True,
                                    timeout=30)
            self.lines = output.stdout.splitlines()


    def parse(self, netid: str) -> None:
        """Build the tree by parsing the sshare output line by line."""
        prev_parent_level_1 = None
        prev_parent_level_2 = None
        prev_parent_level_3 = None
        prev_parent_level_4 = None
        for line in self.lines:
            items = line.split()
            level = len(line) - len(line.lstrip())
            items.append(level)
            if len(items) == 9:
                # user level
                account = items[0]
                user = items[1]
                self.tree.create_node(tag=account,
                                      identifier=f"{account} ({user})",
                                      parent=current_parent,
                                      data=TreeNode(*items))
                if netid == user:
                    self.num_accounts += 1
            elif len(items) == 7:
                # non-user association
                items.insert(1, "--")
                items.insert(6, "--")
                account = items[0]
                user = items[1]
                if level == 1:
                    current_parent = "root (--)"
                elif level == 2 and prev_parent_level_1:
                    current_parent = prev_parent_level_1
                elif level == 3 and prev_parent_level_2:
                    current_parent = prev_parent_level_2
                elif level == 4 and prev_parent_level_3:
                    current_parent = prev_parent_level_3
                self.tree.create_node(tag=account,
                                      identifier=f"{account} ({user})",
                                      parent=current_parent,
                                      data=TreeNode(*items))
                if level == 1:
                   prev_parent_level_1 = f"{account} ({user})"
                elif level == 2:
                   prev_parent_level_2 = f"{account} ({user})"
                elif level == 3:
                   prev_parent_level_3 = f"{account} ({user})"
                elif level == 4:
                   prev_parent_level_4 = f"{account} ({user})"
                current_parent = f"{account} ({user})"

            elif len(items) == 5:
                # root node
                items.insert(1, "--")
                items.insert(2, "--")
                items.insert(6, "--")
                items.insert(7, "--")
                self.tree.create_node(tag="ROOT",
                                      identifier="root (--)",
                                      data=TreeNode(*items))
                current_parent = "root (--)"
            else:
                raise ValueError(f"ERROR: row found with {len(items)} items ({line})")


    def analyze(self) -> str:
        if len(self.tree) == 0:
            return "INFO: The tree is empty."
        self.tree.show(idhidden=False)
        s = "DEBUG\n=====\n"
        s += f"Root node: {self.tree.root}\n"
        s += f"Level 1 nodes: {[item.identifier for item in self.tree.children('root (--)')]}\n"
        s += f"Tree size: {self.tree.size()}\n"
        s += f"Leaves count: {len(self.tree.leaves())}\n\n"
        s += f"Tree depth: {self.tree.depth()}\n"
        s += f"Is total (--) in tree? {'total (--)' in self.tree}\n"
        return s


    def display_siblings(self, node_id: str) -> str:
        """Print the siblings for the given node identifier."""
        # compute proportion of rawusage
        return "\n".join([str(s.data) for s in self.tree.siblings(node_id)])


    def research_group_table(self, node_id: str, netid: str) -> str:
        """Return a string of the rows of the research group table sorted by
           RawUsage."""
        members = [[self.tree[node_id].data.user,
                   int(self.tree[node_id].data.raw_usage),
                   float(self.tree[node_id].data.fair_share),
                   self.tree[node_id].data.level_fs]]
        for sibling in self.tree.siblings(node_id):
            members.append([sibling.data.user,
                            int(sibling.data.raw_usage),
                            float(sibling.data.fair_share),
                            sibling.data.level_fs])
        members.sort(key=lambda x: x[1], reverse=True)
        w_idx = 4
        w_name = 10
        w_dept = 14
        w_sal = 14
        #TODO add proportions
        s = f"{'':>{w_idx}} {'User':>{w_name}} {'RawUsage':>{w_dept}} {'Fairshare':>{w_sal}} {'LevelFS':>{w_sal}}\n"
        for i, member in enumerate(members):
            idx, user, usage, fs, lfs = i + 1, member[0], member[1], member[2], member[3]
            if user == netid:
               idx = self.colorize(idx, color="red")
               user = self.colorize(user, color="red")
               usage = self.colorize(usage, color="red")
            s += f"{idx:>{w_idx}} {user:>{w_name}} {usage:>{w_dept}} {fs:>{w_sal},.5f} {lfs:>{w_sal}}\n"
        return s


    @staticmethod
    def add_proportions(values: List[str], decimals: int=0) -> List[str]:
        """Add the proportion of each value in parentheses."""
        if values == []:
            return []
        values = list(map(int, values))
        total = sum(values)
        if total == 0:
            proportions = ["(--)"] * len(values)
        else:
            if decimals == 0:
                proportions = [f"({round(100 * value / total)}%)" for value in values]
            else:
                proportions = [f"({round(100 * value / total, decimals)}%)" for value in values]
        width_pro = max(map(len, proportions))
        vp = []
        for v, p in zip(values, proportions):
            spaces = " " * (width_pro - len(p) + 1)
            vp.append(f"{str(v)}{spaces}{p}")
        return vp


    def depts_with_shares(self, node_id: str, decimals: int=0) -> str:
        """List the departments/groups and their shares. This allows users to
           see who has contributed."""
        rows = []
        for child in self.tree.children(node_id):
            rows.append([child.data.account,
                         int(child.data.raw_shares),
                         child.data.raw_usage,
                         child.data.level_fs])
        rows.sort(key=lambda x: x[1], reverse=True)
        account = []
        shares = []
        usage = []
        lfs = []
        for row in rows:
            ac, sh, us, lf = row
            account.append(ac)
            shares.append(str(sh))
            usage.append(us)
            lfs.append(lf.replace("inf", "Infinity"))
        shares = self.add_proportions(shares, decimals)
        width_idx = len(str(len(account)))
        width_account = max(len("Account"), max(map(len, account)))
        width_shares = max(len("Shares"), max(map(len, shares)))
        width_usage = max(len("RawUsage"), max(map(len, usage)))
        width_lfs = max(len("LevelFS"), max(map(len, lfs)))
        sp = " " * 3
        rows = f"{'':>{width_idx}} {'Account ':>{width_account}}{sp}{'Shares   ':>{width_shares}}{sp}{'Usage  ':>{width_usage}}{sp}{'LevelFS ':>{width_lfs}}\n"
        rows += f"{' ' * width_idx} {'-' * (width_account + width_shares + width_usage + width_lfs + 3 * len(sp))}\n"
        for i, (ac, sh, us, lf) in enumerate(zip(account, shares, usage, lfs)):
            rows += f"{i+1:>{width_idx}} {ac:>{width_account}}{sp}{sh:>{width_shares}}{sp}{us:>{width_usage}}{sp}{lf:>{width_lfs}}\n"
        return rows


    def fairshare_rank(self, fs: float) -> str:
        """Estimate the rank of the user. One could determine it exactly but
           not so important."""
        total_users = len(self.tree.leaves())
        rank = int(total_users * (1 - fs))
        rank = max(1, rank)
        return f"Rank: {rank} of {total_users} or {round(100 * (1 - rank / total_users))}%"


    def is_pli(self, node_id: str) -> bool:
        """Return True if the node is under PLI else False."""
        return self.tree.is_ancestor("pli (--)", node_id)


    @staticmethod
    def dept_share_as_percentage(shares: int, total: int) -> Union[int, float]:
        """Return a formatted version of the percentage of raw shares of the
           department."""
        pct = 100 * shares / total
        if pct < 0.5:
            return round(pct, 5)
        return round(pct)


    def get_dept(self, node_id: str) -> str:
        """Return information about the department of the user."""
        if not self.is_pli(node_id):
            total = self.get_total_shares()
            dept = self.tree.ancestor(node_id, level=2)
            pct = self.dept_share_as_percentage(int(dept.data.raw_shares), total)
            return f"{dept.data.account}: {dept.data.raw_shares}/{total} or {pct}%"
        return "PLI: 300"


    def get_total_shares(self) -> int:
        """Get level 2 shares ignoring PLI."""
        total = 0
        for child in self.tree.children("total (--)"):
            total += int(child.data.raw_shares)
        return total


    def get_levelfs_rank(self, node_id: str) -> str:
        """Return the rank of the LevelFS values at the level of the specified
           node."""
        levelfs = [self.tree[node_id].data.level_fs]
        for sibling in self.tree.siblings(node_id):
            levelfs.append(sibling.data.level_fs)
        if levelfs[0] == ["inf"]:
            return "1 of {len(levelfs)}"
        pairs = []
        for i, lf in enumerate(levelfs):
            lf = float('inf') if lf == "inf" else float(lf)
            pairs.append((i, lf))
        pairs.sort(key=lambda x: x[1], reverse=True)
        for j, (i, lf) in enumerate(pairs):
            if i == 0:
                return f"{j + 1} of {len(pairs)}"


    def draw_subtree(self, node_id: str) -> None:
        """Draw the subtree from root to the specified node."""
        path = list(self.tree.rsearch(node_id))
        path.reverse()
        path_names = [self.tree[node_id].identifier for node_id in path]
        tree = Tree()
        tree.create_node(tag=path_names[0].split()[0], identifier=path_names[0])
        parent = path_names[0]
        term = Terminal()
        user = path_names[-1].split("(")[-1].replace(")", "")
        user = f"{term.bold}{user}{term.normal}"
        for i, p in enumerate(path_names[1:]):
            rank = self.get_levelfs_rank(p)
            num_users = len(self.tree.leaves(p))
            if i + 1 == len(path_names[1:]):
                tree.create_node(tag=f"{user} (LevelFS Rank: {rank})", identifier=p, parent=parent)
            else:
                tree.create_node(tag=f"{p.split()[0]} (LevelFS Rank: {rank}, Num Users: {num_users})", identifier=p, parent=parent)
            parent = p
        tree.show()


    @staticmethod
    def colorize(txt: Union[str, int, float], style: str="normal", color: str="black") -> str:
        term = Terminal()
        if not blessed_is_available:
            return txt
        if not isinstance(txt, str):
            txt = str(txt)
        if color == "red":
            txt = f"{term.red}{txt}"
        elif color == "green":
            txt = f"{term.green}{txt}"
        if style == "bold":
            txt = f"{term.bold}{txt}"
        return f"{txt}{term.normal}"



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="myshare - Shares of a user in plain language")
    parser.add_argument("-u", "--user", type=str, default=os.environ["USER"], help="NetID of the user")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show more details")
    parser.add_argument("-d", "--debug", action="store_true", help="Print debug info")
    args = parser.parse_args()

    mytree = ShareTree()
    mytree.get_raw_data()
    mytree.parse(args.user)
    if args.debug:
        print(mytree.analyze())

    """
    node_id = "whitece (yl3095)"
    print(mytree.display_siblings(node_id))
    parent = mytree.tree.parent(node_id)
    print(parent)
    parent = mytree.tree.parent(parent.identifier)
    print(parent)

    under_total = True if mytree.tree.is_ancestor("total (--)", node_id) else False
    print(under_total)
    under_total = True if mytree.tree.is_ancestor("total (--)", "pli (hyen)") else False
    print(under_total)
    """

    # do we do a first pass to figure out number of accounts and in PLI?
    # or use config.py to handle cases
    for node_id in mytree.tree.expand_tree():
        if node_id.endswith(f" ({args.user})"):
            path = list(mytree.tree.rsearch(node_id))
            path.reverse()
            path_names = [mytree.tree[node_id].identifier.split()[0] for node_id in path]
            print(f"Tree: {' > '.join(path_names)}")
            print(f"User: {mytree.tree[node_id].data.user}")
            print(f"Account: {mytree.tree[node_id].data.account}")
            fs = float(mytree.tree[node_id].data.fair_share)
            fs_color = mytree.colorize(fs, style="bold", color="green")
            print(f"Fairshare: {fs_color} ({mytree.fairshare_rank(fs)})")
            print(f"LevelFS: {mytree.tree[node_id].data.level_fs}")
            print(f"Department shares: {mytree.get_dept(node_id)}\n")
            print("Good news! The 'cbe' Slurm association has ...You are in a department with lots of shares.")
            print("\n\nHere are the departments sorted by contributions or shares:\n\n")
            print("\n\nBy Research Group\n\n")
            #level3 = mytree.tree.parent(node_id).identifier
            level3 = mytree.tree.ancestor(node_id, level=2).identifier
            print(mytree.depts_with_shares(node_id=level3, decimals=1))
            print(mytree.depts_with_shares(node_id="total (--)", decimals=1))
            s = ("Accounts with LevelFS > 1 have been under-served by Slurm. User within "
                 "those accounts will receive a priority boost. Similarly, accounts with "
                 "LevelFS < 1 will receive a priority penalty since they have been over-served. "
                 "When all accounts are running heavily the the shares breakdown  will "
                 "reflect where the resources are allocated. The shares column"
                 "reflects the limiting distribution or what to expect over long times. "
                 "The good news for users in a department with 1 or a small number of "
                 "shares is that the contributing departments often run fewer jobs "
                 "for periods of time. Then the effective shares increases for everyone else.\n")
            print(s)
            print("Your fairshare is approximately equal to 1 - levelFS rank@dept / num_depts\n")
            print("More important than shares is your LevelFS Rank at level 2\n")
            print("\n\nBelow is the 'webb' research group under the 'cbe' association:\n\n")
            print(mytree.research_group_table(node_id, args.user))
            mytree.draw_subtree(node_id)
            print(mytree.get_levelfs_rank("cbe (--)"))
            print("cbe users:", len(mytree.tree.leaves("cbe (--)")))
            print("\n\n==============================================================================\n\n")

    #mytree.tree.show(data_property="fair_share")

    node_id = "total (--)"
    #print(mytree.depts_with_shares(node_id))

    #mytree.tree.show(nid="cee (--)")

    print(c.MORE_INFO_URL)
