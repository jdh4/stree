"""Assume 'sponsor (user)' is unique over the tree. Will get conflicts otherwise.
   Same is true with 'association (--)'. Could use uid to resolve the first issue."""


import subprocess
from textwrap import TextWrapper
from treelib import Tree
from treelib import Node as TreeLibNode
from treelib.exceptions import DuplicatedNodeIdError
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
                 level_fs):
        self.account = account
        self.user = user
        self.raw_shares = raw_shares
        self.norm_shares = norm_shares
        self.raw_usage = raw_usage
        self.effectv_usage = effectv_usage
        self.fair_share = fair_share
        self.level_fs = level_fs

    def __str__(self):
        return (f"level: {self.level}, account: {self.account}, user: {self.user}, raw shares: {self.raw_shares}, "
                f"effective usage: {self.effectv_usage}, fs: {self.fair_share}")




class ShareTreeError(Exception):
    pass




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
        parent_at_level = {-1: "root (--)"}
        current_parent = "root (--)"
        for line in self.lines:
            if not line.strip():
                continue
            level = len(line) - len(line.lstrip())
            items = line.split()

            # root node
            if len(items) == 4:
                items.insert(1, "--")
                items.insert(2, "--")
                items.insert(6, "--")
                items.insert(7, "--")
                self.tree.create_node(tag="ROOT",
                                      identifier="root (--)",
                                      data=TreeNode(*items))
                parent_at_level[level] = "root (--)"
                continue

            account = items[0]
            user = items[1]
            identifier = f"{account} ({user})"

            parent_level = max([lvl for lvl in parent_at_level.keys() if lvl < level], default=-1)
            current_parent = parent_at_level[parent_level]

            if len(items) == 8:
                # user level
                self.tree.create_node(tag=account,
                                      identifier=identifier,
                                      parent=current_parent,
                                      data=TreeNode(*items))
                if netid == user:
                    self.num_accounts += 1
            elif len(items) == 6:
                # non-user association
                items.insert(1, "--")
                items.insert(6, "--")
                identifier = f"{account} ({items[1]})"
                try:
                    self.tree.create_node(tag=account,
                                          identifier=identifier,
                                          parent=current_parent,
                                          data=TreeNode(*items))
                except DuplicatedNodeIdError as e:
                    msg = f"Node '{identifier}' already exists (Details: {e})."
                    raise ShareTreeError(msg) from e
                else:
                    parent_at_level[level] = identifier
            else:
                msg = f"ERROR: row found with {len(items)} items ({line})"
                raise ValueError(msg)


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


    @staticmethod
    def add_proportions(values: List[str], decimals: int = 0) -> List[str]:
        """Add the proportion of each value in parentheses."""
        if values == []:
            return []
        int_values = [int(v) for v in values]
        total = sum(int_values)
        if total == 0:
            proportions = ["(--)"] * len(int_values)
        else:
            proportions = [f"({v / total:.{decimals}%})" for v in int_values]
        width_pro = max(len(p) for p in proportions)
        return [f"{v} {p:>{width_pro}}" for v, p in zip(int_values, proportions)]


    def number_of_active_users(self, node_id: str) -> int:
        """Return the number of users with usage greater than zero in the
           descendant nodes of the specified parent node."""
        num_active_users = 0
        for leaf in self.tree.leaves(node_id):
            if "(--)" not in leaf.identifier and leaf.data.raw_usage.isdigit() and int(leaf.data.raw_usage) > 0:
                num_active_users += 1
        return num_active_users


    def min_max_fairshare(self, descendant: TreeLibNode) -> Tuple[str, str]:
        """Return tuple of min and max fairshare values of the leaves of the
           subtree of the specified node (descendant)."""
        if descendant.is_leaf():
            return ("--", "--")
        nodes = self.tree.leaves(descendant.identifier)
        values = [float(node.data.fair_share)
                  for node in nodes
                  if node.data.fair_share != "--"]
        if not values:
            return ("--", "--")
        minimum = min(values)
        maximum = max(values)
        return (f"{minimum:.6f}", f"{maximum:.6f}")


    def get_descendants_table(self,
                              node_id: str,
                              sort_by: str="LevelFS",
                              decimals: int=0,
                              tabbing: int=0,
                              user_dept: str="",
                              fields: Tuple[str, ...] = ()) -> str:
        """Return a table of the children or all descendants of the specified
           parent node. This can be used to show which high-level associations
           have contributed."""
        if self.tree[node_id].is_leaf():
            return f"No table since '{node_id}' is a leaf node."

        user_level = True if self.tree.children(node_id)[0].is_leaf() else False
        rows = []
        if fields == ("Account", "User", "Shares", "Usage"):
            descendants = [leaf for leaf in self.tree.leaves(node_id) if "(--)" not in leaf.identifier]
        else:
            descendants = self.tree.children(node_id)
        # not necessarily at child so name should change
        for child in descendants:
            num_active_users = self.number_of_active_users(child.identifier)
            minfs, maxfs = self.min_max_fairshare(child)
            rows.append([child.data.account,
                         child.data.user,
                         int(child.data.raw_shares),
                         int(child.data.raw_usage),
                         child.data.fair_share,
                         float(child.data.level_fs),
                         num_active_users,
                         minfs,
                         maxfs])
        if sort_by == "LevelFS":
            rows.sort(key=lambda x: x[5], reverse=True)
        elif sort_by == "RawShares":
            rows.sort(key=lambda x: x[2], reverse=True)
        elif sort_by == "Usage":
            rows.sort(key=lambda x: x[3], reverse=True)
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
            usage.append(str(us))
            fair.append(fr)
            lfs.append(self.format_levelfs(lf))
            users.append(ct)
            minfs.append(mn)
            maxfs.append(mx)
        if len(set(shares)) > 1:
            shares = self.add_proportions(shares, decimals)
        usage = self.add_proportions(usage, decimals=0)
        width_idx = len(str(len(user))) if user_level else len(str(len(account)))
        width_account = max(len("Account "), max(map(len, account)))
        width_user = max(len("User"), max(map(len, user)))
        width_shares = max(len("Shares  "), max(map(len, shares)))
        width_usage = max(len("Usage    "), max(map(len, usage)))
        width_fair = max(len("FairShare"), max(map(len, fair)))
        width_lfs = max(len("LevelFS "), max(map(len, lfs)))
        width_users = max(len("ActiveUsers"), max(map(len, map(str, users))))
        width_minfs = max(len("min(FairShare)"), max(map(len, minfs)))
        width_maxfs = max(len("max(FairShare)"), max(map(len, maxfs)))
        sp = " " * 3
        tb = " " * 5 * tabbing
        term = Terminal()
        #print(self.tree.level(node_id), self.tree[node_id].data.account)
        if tabbing == -1:
            rows = f"{'':>{width_idx}}  {'Account ':>{width_account}}{sp}{'Shares   ':>{width_shares}}{sp}{'Usage    ':>{width_usage}}{sp}{'LevelFS ':>{width_lfs}}{sp}{'ActiveUsers ':>{width_users}}\n"
            rows += f"{' ' * width_idx}  {'─' * (width_account + width_shares + width_usage + width_lfs + width_users + 4 * len(sp))}\n"
            for i, (ac, sh, us, lf, ct, mn, mx) in enumerate(zip(account, shares, usage, lfs, users, minfs, maxfs)):
                rows += f"{i+1:>{width_idx}}  {ac:>{width_account}}{sp}{sh:>{width_shares}}{sp}{us:>{width_usage}}{sp}{lf:>{width_lfs}}{sp}{ct:>{width_users}}\n"
            return rows
        if tabbing == -2:
            rows = f"{'':>{width_idx}}  {'Account ':>{width_account}}{sp}{'User ':>{width_user}}{sp}{'Shares   ':>{width_shares}}{sp}{'Usage    ':>{width_usage}}{sp}{'LevelFS ':>{width_lfs}}\n"
            rows += f"{' ' * width_idx}  {'─' * (width_account + width_user + width_shares + width_usage + width_lfs + 4 * len(sp))}\n"
            for i, (ac, ur, sh, us, lf, ct, mn, mx) in enumerate(zip(account, user, shares, usage, lfs, users, minfs, maxfs)):
                rows += f"{i+1:>{width_idx}}  {ac:>{width_account}}{sp}{ur:>{width_user}}{sp}{sh:>{width_shares}}{sp}{us:>{width_usage}}{sp}{lf:>{width_lfs}}\n"
            return rows
        if user_level:
            rows = f"{tb}| {'':>{width_idx}}  {'User ':>{width_user}}{sp}{'Usage    ':>{width_usage}}{sp}{'LevelFS ':>{width_lfs}}{sp}{'FairShare':>{width_fair}}\n"
            rows += f"{tb}| {' ' * width_idx}  {'─' * (width_user + width_usage + width_lfs + width_fair + 3 * len(sp))}\n"
            for i, (ur, us, lf, fr) in enumerate(zip(user, usage, lfs, fair)):
                rows += f"{tb}| {i+1:>{width_idx}}  {ur:>{width_user}}{sp}{us:>{width_usage}}{sp}{lf:>{width_lfs}}{sp}{fr:>{width_fair}}\n"
        else:
            rows = f"{tb}| {'':>{width_idx}}  {'Account ':>{width_account}}{sp}{'Shares   ':>{width_shares}}{sp}{'Usage    ':>{width_usage}}{sp}{'LevelFS ':>{width_lfs}}{sp}{'ActiveUsers ':>{width_users}}{sp}{'min(FairShare)':>{width_minfs}}{sp}{'max(FairShare)':>{width_maxfs}}\n"
            rows += f"{tb}| {' ' * width_idx}  {'─' * (width_account + width_shares + width_usage + width_lfs + width_users + width_minfs + width_maxfs + 6 * len(sp))}\n"
            for i, (ac, sh, us, lf, ct, mn, mx) in enumerate(zip(account, shares, usage, lfs, users, minfs, maxfs)):
                if node_id == "total (--)" and ac == user_dept:
                    rows += f"{tb}| {term.bold}{term.blue}{i+1:>{width_idx}}  {ac:>{width_account}}{sp}{sh:>{width_shares}}{sp}{us:>{width_usage}}{sp}{lf:>{width_lfs}}{sp}{ct:>{width_users}}{sp}{mn:>{width_minfs}}{sp}{mx:>{width_maxfs}}{term.normal}\n"
                else:
                    rows += f"{tb}| {i+1:>{width_idx}}  {ac:>{width_account}}{sp}{sh:>{width_shares}}{sp}{us:>{width_usage}}{sp}{lf:>{width_lfs}}{sp}{ct:>{width_users}}{sp}{mn:>{width_minfs}}{sp}{mx:>{width_maxfs}}\n"
        return rows


    @staticmethod
    def format_percentile(n: int) -> str:
        """Converts a percentile integer (0-100) to its ordinal string
           representation."""
        if not (0 <= n <= 100):
            raise ValueError("Percentile must be between 0 and 100.")
        if 11 <= n % 100 <= 13:
            return f"{n}th"
        last_digit = n % 10
        if last_digit == 1:
            return f"{n}st"
        elif last_digit == 2:
            return f"{n}nd"
        elif last_digit == 3:
            return f"{n}rd"
        else:
            return f"{n}th"


    def fairshare_rank(self, fs: float) -> Tuple[str, str, str]:
        """Estimate the rank of the user. One could determine it exactly but
           not so important. Note that the total number of users is used
           instead of the active number of users (where usage > 0)."""
        # TODO: maybe this only applies under total (--) since root (root)
        # it also includes pli but that is expected
        total_users = sum(1 for leaf in self.tree.leaves() if "(--)" not in leaf.identifier)
        if total_users == 0:
            return ("0 of 0", "0", "bottom")
        raw_rank = round(total_users * (1 - fs))
        rank = max(1, min(total_users, raw_rank))
        pct = 100 if rank == 1 else round(100 * (1 - rank / total_users))
        direction = "top" if pct >= 50 else "bottom"
        pct_fmt = ShareTree.format_percentile(pct)
        return (f"{rank} of {total_users}", pct_fmt, direction)


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


    def get_total_shares(self, node_id: str = "total (--)") -> int:
        """Return the total shares of the children of the specified parent node.
           Shares that are non-integers are skipped."""
        total = 0
        for child in self.tree.children(node_id):
            if child.data.raw_shares.isdigit():
                total += int(child.data.raw_shares)
        return total


    def get_dept(self, node_id: str) -> str:
        """Return information about the department of the user."""
        if not self.is_pli(node_id):
            total = self.get_total_shares()
            dept = self.tree.ancestor(node_id, level=2)
            pct = self.dept_share_as_percentage(int(dept.data.raw_shares), total)
            return f"{dept.data.account}: {dept.data.raw_shares}/{total} or {pct}%"
        return "PLI: 300"


    def get_levelfs_rank(self, node_id: str) -> str:
        """Return the rank of the LevelFS values at the level of the specified
           node."""
        target_fs_raw = self.tree[node_id].data.level_fs
        siblings = self.tree.siblings(node_id)
        total_nodes = 1 + len(siblings)
        if target_fs_raw == "inf":
            return f"1/{total_nodes}"
        target_val = float(target_fs_raw)
        rank = 1
        for sibling in siblings:
            sib_fs_raw = sibling.data.level_fs
            sib_val = float('inf') if sib_fs_raw == "inf" else float(sib_fs_raw)
            if sib_val > target_val:
                rank += 1
        return f"{rank}/{total_nodes}"


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


    # TODO trailing 0 getting lost
    @staticmethod
    def format_fairshare(fs: float) -> str:
        """Format and colorize the fairshare value."""
        fs_str = f"Fairshare: {fs:.6f}"
        padding = " " * ((WIDTH - len(fs_str)) // 2)
        # set default color
        if fs >= 0.75:
            color = "green"
        elif fs <= 0.28:
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
                   "You can expect intermediate to long queue times.")
        elif fs >= 0.0 and fs < 0.25:
            msg = (f"Bad news! You have a low fairshare value of {fs}. Your fairshare "
                   f"rank is {rank} users which puts you in the {direction} {pct} percentile. You can expect "
                   "long queue times. The tree at the top helps explain why your fairshare is low.")
        # Fairshare varies between 0 to 1. The larger the value the larger the contribution to job priority
        return wrapper.fill(msg)
