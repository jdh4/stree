import subprocess
from textwrap import TextWrapper
from treelib import Tree
from typing import Optional
from typing import Union
from typing import List
from typing import Tuple
#import config as c
try:
    from blessed import Terminal
    blessed_is_available = True
except ModuleNotFoundError:
    blessed_is_available = False

WIDTH = 80


class TreeNode:

    """Represents a single node (Account or User) in the sshare hierarchy."""
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
        """Create a tree instance and initialize num_accounts which tracks the
           number of accounts for the user."""
        self.lines = []
        self.tree = Tree()
        self.num_accounts = 0


    def get_raw_data(self, text: Optional[str] = None) -> None:
        """Get the data from either sacct or a string to build the tree. The
           string makes it possible to test the code."""
        if text:
            self.lines = text.splitlines()
        else:
            fmt = "Account,User,RawShares,NormShares,RawUsage,EffectvUsage,FairShare,LevelFS"
            cmd = ["sshare", "-a", "-l", "-n", "-o", fmt]
            output = subprocess.run(cmd,
                                    stdout=subprocess.PIPE,
                                    encoding="utf8",
                                    check=True,
                                    text=True,
                                    shell=False,
                                    timeout=30)
            self.lines = output.stdout.splitlines()


    def parse(self, netid: str) -> None:
        """Build the tree by parsing the sshare output line by line."""
        #TODO remove level in node
        current_parent = "root (--)"
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
                elif level == 5 and prev_parent_level_4:
                    current_parent = prev_parent_level_4
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
        """Print the siblings for the given node identifier. This ignores the
           specified node in the output."""
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

    #def format_levelfs_column(values: List[str]) -> List[str]:



    def depts_with_shares(self,
                          node_id: str,
                          sort_by: str="LevelFS",
                          decimals: int=0,
                          tabbing: int=0,
                          user_dept: str="") -> str:
        """List the data of the children of the specified parent. This can be
           used to show which high-level associations have contributed."""
        user_level = True if self.tree.children(node_id)[0].is_leaf() else False
        rows = []
        for child in self.tree.children(node_id):
            minfs = "--"
            maxfs = "--"
            if node_id == "total (--)" or not user_level:
                if not child.is_leaf():
                    nodes = self.tree.leaves(child.identifier)
                    minfs = min([float(node.data.fair_share) for node in nodes if "(--)" not in node.identifier])
                    maxfs = max([float(node.data.fair_share) for node in nodes if "(--)" not in node.identifier])
            minfs = minfs if minfs == "--" else str(round(minfs, 5))
            maxfs = maxfs if maxfs == "--" else str(round(maxfs, 5))
            if minfs != "--" and len(minfs) <= 6:
                minfs += "0" * (7 - len(minfs))
            if maxfs != "--" and len(maxfs) <= 6:
                maxfs += "0" * (7 - len(maxfs))
            rows.append([child.data.account,
                         child.data.user,
                         int(child.data.raw_shares),
                         child.data.raw_usage,
                         child.data.fair_share,
                         float(child.data.level_fs),
                         len([leaf for leaf in self.tree.leaves(child.identifier) if "(--)" not in leaf.identifier]),
                         minfs,
                         maxfs])
        if sort_by == "LevelFS":
            rows.sort(key=lambda x: x[5], reverse=True)
        else:
            rows.sort(key=lambda x: x[2], reverse=True)
        account = []
        user = []
        shares = []
        usage = []
        fair = []
        lfs = []
        users = []
        minfs = []
        maxfs = []
        for row in rows:
            ac, ur, sh, us, fr, lf, ct, mn, mx = row
            account.append(ac)
            user.append(ur)
            shares.append(str(sh))
            usage.append(us)
            fair.append(fr)
            lfs.append(self.format_levelfs(lf))
            users.append(ct)
            minfs.append(mn)
            maxfs.append(mx)
        shares = self.add_proportions(shares, decimals)
        width_idx = len(str(len(user))) if user_level else len(str(len(account)))
        width_account = max(len("Account"), max(map(len, account)))
        width_user = max(len("User"), max(map(len, user)))
        width_shares = max(len("Shares"), max(map(len, shares)))
        width_usage = max(len("RawUsage"), max(map(len, usage)))
        width_fair = max(len("FairShare"), max(map(len, fair)))
        width_lfs = max(len("LevelFS"), max(map(len, lfs)))
        width_users = max(len("NumUsers"), max(map(len, map(str, users))))
        width_minfs = max(len("min(FairShare)"), max(map(len, minfs)))
        width_maxfs = max(len("max(FairShare)"), max(map(len, maxfs)))
        sp = " " * 3
        tb = " " * 5 * tabbing
        term = Terminal()
        #print(self.tree.level(node_id), self.tree[node_id].data.account)
        if user_level:
            rows = f"{tb}| {'':>{width_idx}}  {'User ':>{width_user}}{sp}{'Usage  ':>{width_usage}}{sp}{'LevelFS ':>{width_lfs}}{sp}{'FairShare':>{width_fair}}\n"
            rows += f"{tb}| {' ' * width_idx}  {'-' * (width_user + width_usage + width_lfs + width_fair + 3 * len(sp))}\n"
            for i, (ur, us, lf, fr) in enumerate(zip(user, usage, lfs, fair)):
                rows += f"{tb}| {i+1:>{width_idx}}  {ur:>{width_user}}{sp}{us:>{width_usage}}{sp}{lf:>{width_lfs}}{sp}{fr:>{width_fair}}\n"
        else:
            rows = f"{tb}| {'':>{width_idx}}  {'Account ':>{width_account}}{sp}{'Shares   ':>{width_shares}}{sp}{'Usage  ':>{width_usage}}{sp}{'LevelFS ':>{width_lfs}}{sp}{'NumUsers ':>{width_users}}{sp}{'min(FairShare)':>{width_minfs}}{sp}{'max(FairShare)':>{width_maxfs}}\n"
            rows += f"{tb}| {' ' * width_idx}  {'-' * (width_account + width_shares + width_usage + width_lfs + width_users + width_minfs + width_maxfs + 6 * len(sp))}\n"
            for i, (ac, sh, us, lf, ct, mn, mx) in enumerate(zip(account, shares, usage, lfs, users, minfs, maxfs)):
                if node_id == "total (--)" and ac == user_dept:
                    rows += f"{tb}| {term.bold}{term.blue}{i+1:>{width_idx}}  {ac:>{width_account}}{sp}{sh:>{width_shares}}{sp}{us:>{width_usage}}{sp}{lf:>{width_lfs}}{sp}{ct:>{width_users}}{sp}{mn:>{width_minfs}}{sp}{mx:>{width_maxfs}}{term.normal}\n"
                else:
                    rows += f"{tb}| {i+1:>{width_idx}}  {ac:>{width_account}}{sp}{sh:>{width_shares}}{sp}{us:>{width_usage}}{sp}{lf:>{width_lfs}}{sp}{ct:>{width_users}}{sp}{mn:>{width_minfs}}{sp}{mx:>{width_maxfs}}\n"
        return rows


    def fairshare_rank(self, fs: float) -> Tuple[str, str, str]:
        """Estimate the rank of the user. One could determine it exactly but
           not so important."""
        total_users = len([leaf for leaf in self.tree.leaves() if "(--)" not in leaf.identifier])
        rank = int(total_users * (1 - fs))
        rank = max(1, rank)
        pct = round(100 * (1 - rank / total_users))
        direction = "top" if pct >= 50 else "bottom"
        return (f"{rank} of {total_users}", f"{pct}", direction)


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


    def get_total_shares(self, node_id: str = "total (--)") -> int:
        """Return the total shares of the children of the specified parent node."""
        total = 0
        for child in self.tree.children(node_id):
            if child.data.raw_shares.isdigit():
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
                return f"{j + 1}/{len(pairs)}"


    @staticmethod
    def format_levelfs(lfs: float) -> str:
        """Format a LevelFS value for display."""
        if lfs == float("inf"):
            return "infinity"
        if lfs == 0.0:
            return "0"
        if lfs < 0.00001:
            return f"{lfs:.2e}"
        elif lfs < 0.0001:
            return str(round(lfs, 5))
        elif lfs < 0.001:
            return str(round(lfs, 4))
        elif lfs < 0.01:
            return str(round(lfs, 3))
        elif lfs < 0.1:
            return str(round(lfs, 2))
        elif lfs < 1:
            return str(round(lfs, 1))
        elif lfs <= 99999999:
            return str(round(lfs))
        else:
            return f"{lfs:.2e}"


    def draw_subtree(self, node_id: str, netid: str) -> None:
        """Draw the subtree from root to the specified node."""
        path = list(self.tree.rsearch(node_id))
        path.reverse()
        path_names = [self.tree[node_id].identifier for node_id in path]
        tree = Tree()
        tree.create_node(tag=path_names[0].split()[0], identifier=path_names[0])
        parent = path_names[0]
        term = Terminal()
        user = f"{term.bold}{netid}{term.normal}"
        total_shares = self.get_total_shares()
        for i, p in enumerate(path_names[1:]):
            rank = self.get_levelfs_rank(p)
            level = self.format_levelfs(float(self.tree[p].data.level_fs))
            shares = self.tree[p].data.raw_shares
            if p == "total (--)":
                tree.create_node(tag=f"{p.split()[0]}", identifier=p, parent=parent)
            elif i + 1 == len(path_names[1:]):
                tree.create_node(tag=f"{user} (LevelFS: {level}, LevelFS Rank: {rank})", identifier=p, parent=parent)
            elif i == 1:
                tree.create_node(tag=f"{p.split()[0]} (LevelFS: {level}, LevelFS Rank: {rank}, Shares: {shares}/{total_shares})", identifier=p, parent=parent)
            else:
                tree.create_node(tag=f"{p.split()[0]} (LevelFS: {level}, LevelFS Rank: {rank})", identifier=p, parent=parent)
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


    @staticmethod
    def format_fairshare(fs: float) -> str:
        """Format and colorize the fairshare value."""
        fs_str = f"Fairshare: {fs}"
        padding = " " * ((WIDTH - len(fs_str)) // 2)
        # set default color
        if fs >= 0.75:
            color = "green"
        elif fs <= 0.25:
            color = "red"
        else:
            color = "black"
        fs_color = ShareTree.colorize(fs, style="bold", color=color)
        label = ShareTree.colorize("Fairshare:", style="bold", color="black")
        return f"{padding}{label} {fs_color}"


    def explain(self, fs: float) -> str:
        """Return an explain of the fairshare of the user and what they can
           expect for queue times."""
        rank, pct, direction = self.fairshare_rank(fs)
        wrapper = TextWrapper(width=WIDTH)
        if fs >= 0.75:
            msg = (f"Good news! You have a high fairshare value of {fs}. Your fairshare "
                   f"rank is {rank} users which puts you in the {direction} {pct} percentile. "
                  "You should expect short queue times for small to intermediate size jobs.")
        elif fs >= 0.25 and fs < 0.75:
            msg = (f"You have a fairshare value of {fs}. Your fairshare rank is {rank} users which puts you in the {direction} {pct} percentile. "
                   "You can expect intermediate queue times.")
        elif fs >= 0.0 and fs < 0.25:
            msg = (f"Bad news! You have a low fairshare value of {fs}. Your fairshare "
                   f"rank is {rank} users which puts you in the {direction} {pct} percentile. You can expect "
                   "long queue times. The tree at the top helps explain why your fairshare is low.")
        # Fairshare varies between 0 to 1. The larger the value the larger the contribution to job priority
        return wrapper.fill(msg)
