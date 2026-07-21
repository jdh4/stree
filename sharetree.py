"""Assume 'sponsor (user)' is unique over the tree. Will get conflicts otherwise.
   Same is true with 'association (--)'. Could use uid to resolve the first issue."""


import subprocess
import textwrap
from treelib import Tree
from treelib import Node as TreeLibNode
from treelib.exceptions import DuplicatedNodeIdError
from typing import Optional
from typing import Union
from typing import List
from typing import Tuple
from typing import Dict
import config as c
try:
    from blessed import Terminal
    blessed_is_available = True
except ModuleNotFoundError:
    blessed_is_available = False

#TODO move to config
WIDTH = 80


class TreeNode:

    """Represents a single node (Account or User) in the sshare hierarchy."""
    def __init__(self,
                 account: str,
                 user: str,
                 raw_shares: str,
                 norm_shares: str,
                 raw_usage: str,
                 effectv_usage: str,
                 fair_share: str,
                 level_fs: str) -> None:
        self.account = account
        self.user = user
        self.raw_shares = raw_shares
        self.norm_shares = norm_shares
        self.raw_usage = raw_usage
        self.effectv_usage = effectv_usage
        self.fair_share = fair_share
        self.level_fs = level_fs

    def __str__(self) -> str:
        return (f"account: {self.account}, user: {self.user}, raw shares: {self.raw_shares}, "
                f"effective usage: {self.effectv_usage}, fs: {self.fair_share}")




class ShareTreeError(Exception):
    pass




class ShareTree:

    def __init__(self) -> None:
        """Create a tree instance and initialize num_accounts which tracks the
           number of accounts for the user."""
        self.lines: List[str] = []
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

            parent_level = max([lvl
                                for lvl in parent_at_level.keys()
                                if lvl < level],
                               default=-1)
            current_parent = parent_at_level[parent_level]

            if len(items) == 8:
                # user level
                self.tree.create_node(tag=account,
                                      identifier=identifier,
                                      parent=current_parent,
                                      data=TreeNode(*items))
                if netid == user:
                    self.num_accounts += 1
            elif len(items) == 5 and "parent" in line:
                # non-user association with RawShares equals "parent"
                items.insert(1, "--")
                items.insert(6, "--")
                # assign LevelFS from parent
                items.insert(7, self.tree[current_parent].data.level_fs)
                # assign RawShares from parent
                items[2] = self.tree[current_parent].data.raw_shares
                identifier = f"{account} ({items[1]})"
                self.tree.create_node(tag=account,
                                      identifier=identifier,
                                      parent=current_parent,
                                      data=TreeNode(*items))
                parent_at_level[level] = identifier
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


    def number_of_active_users(self, node_id: str) -> str:
        """Return the number of users with usage greater than zero in the
           descendant nodes of the specified parent node."""
        num_active_users = 0
        for leaf in self.tree.leaves(node_id):
            if "(--)" not in leaf.identifier and int(leaf.data.raw_usage) > 0:
                num_active_users += 1
        return str(num_active_users)


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
        minimum = self.format_fairshare(min(values))
        maximum = self.format_fairshare(max(values))
        return (minimum, maximum)


    @staticmethod
    def column_width(name: str, values: List[str]) -> Tuple[str, int]:
        """Return a tuple of the column width and padded column name."""
        name_width = len(name)
        values_width = max(map(len, values))
        if values_width <= name_width:
            return (name, name_width)
        num_spaces = (values_width - name_width) // 2
        name_padded = f"{name}{' ' * num_spaces}"
        return (name_padded, values_width)


    @staticmethod
    def create_table(columns: Dict[str, List[str]],
                     show_zero_usage: bool = False,
                     vertical_line: bool = False,
                     indent: str = "",
                     accounts_to_color: Tuple[str, ...] = (),
                     user_to_color: str = "",
                     caption: str = "") -> str:
        """Note that get width of index but that could change since number of
           users with zero Usage not known."""
        if not columns:
            return ""
        term = Terminal()
        num_columns = len(columns)
        names = [""]
        first_column_length = len(next(iter(columns.values())))
        widths = [len(str(first_column_length))]

        index_usage = None
        index_account = None
        index_user = None
        for i, (name, values) in enumerate(columns.items()):
            n, w = ShareTree.column_width(name, values)
            names.append(n)
            widths.append(w)
            if name == "Usage":
                index_usage = i
            elif name == "Account":
                index_account = i
            elif name == "User":
                index_user = i
        sp = " " * 3
        lines = []

        vline = f"{indent}│ " if vertical_line else ""
        header_cells = [f"{vline}{names[0]:>{widths[0]}}"]
        header_cells.extend(f"{n:>{w}}" for n, w in zip(names[1:], widths[1:]))
        lines.append(sp.join(header_cells))

        total_dash_width = sum(widths[1:]) + (num_columns - 1) * len(sp)
        lines.append(f"{vline}{' ' * widths[0]}{sp}{'─' * total_dash_width}")

        row_index = 1
        for vals in zip(*columns.values()):
            if not show_zero_usage and index_usage is not None:
                usage_val = vals[index_usage]
                if usage_val == "0" or usage_val.startswith("0 "):
                    continue
            # TODO only look at first item in accounts to color
            pre, post = "", ""
            if user_to_color or accounts_to_color:
                if index_account is not None and vals[index_account] in accounts_to_color:
                    pre = f"{term.bold}{term.blue}"
                    post = f"{term.normal}"
                if index_user is not None and vals[index_user] == user_to_color:
                    pre = f"{term.bold}{term.blue}"
                    post = f"{term.normal}"
            row_cells = [f"{row_index:>{widths[0]}}"]
            row_cells.extend(f"{val:>{widths[j+1]}}" for j, val in enumerate(vals))
            row_str = sp.join(row_cells)
            lines.append(f"{vline}{pre}{row_str}{post}")
            row_index += 1
        if caption:
            lines.append(f"{vline}")
            for cap in caption.split("\n"):
                lines.append(f"{vline}  {cap}")
        return "\n".join(lines) + "\n"


    def get_descendants_table(self,
                              node_id: str,
                              sort_by: str = "LevelFS",
                              decimals: int = 0,
                              tabbing: int = 0,
                              vertical_line = False,
                              accounts_to_color: Tuple[str, ...] = (),
                              user_to_color: str = "",
                              fields: Tuple[str, ...] = ()) -> str:
        """Return a table of the children or all descendants of the specified
           parent node. This can be used to show which high-level associations
           have contributed."""
        if self.tree[node_id].is_leaf():
            return f'No table since "{node_id.split()[0]}" has no users.'

        rows = []
        if fields == ("User", "Account", "Usage", "LevelFS", "Fairshare"):
            descendants = [leaf
                           for leaf in self.tree.leaves(node_id)
                           if "(--)" not in leaf.identifier]
        elif fields == ("Account", "Shares", "Usage", "LevelFS", "ActiveUsers"):
            descendants = self.tree.children(node_id)
        else:
            descendants = self.tree.children(node_id)
        # not necessarily at child so name should change
        for child in descendants:
            num_active_users = self.number_of_active_users(child.identifier)
            min_fs, max_fs = self.min_max_fairshare(child)
            rows.append([child.data.account,
                         child.data.user,
                         int(child.data.raw_shares),
                         int(child.data.raw_usage),
                         child.data.fair_share,
                         float(child.data.level_fs),
                         num_active_users,
                         min_fs,
                         max_fs])
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
        minmax = []
        for row in rows:
            ac, ur, sh, us, fr, lf, ct, mn, mx = row
            account.append(ac)
            user.append(ur)
            shares.append(str(sh))
            usage.append(str(us))
            fair.append(self.format_fairshare(fr))
            lfs.append(self.format_levelfs(lf, padding=True))
            users.append(ct)
            minfs.append(mn)
            maxfs.append(mx)
            minmax.append(f"[{mn}, {mx}]")
        if len(set(shares)) > 1:
            shares = self.add_proportions(shares, decimals)
        usage = self.add_proportions(usage, decimals=0)

        user_level = True if all([ch.is_leaf() for ch in self.tree.children(node_id)]) else False
        #print("user-level", user_level, [ch.is_leaf() for ch in self.tree.children(node_id)])
        tb = " " * 5 * tabbing

        if fields == ("Account", "Shares", "Usage", "LevelFS", "ActiveUsers") and sort_by == "RawShares":
            # show accounts sorted by shares
            columns = {"Account": account, "Shares": shares, "Usage": usage, "LevelFS": lfs, "ActiveUsers": users}
            table = self.create_table(columns, show_zero_usage=True, accounts_to_color=accounts_to_color)
            return table
        elif fields == ("User", "Account", "Usage", "LevelFS", "Fairshare"):
            # stree -A <account>
            columns = {"User": user, "Account": account, "Usage": usage, "LevelFS": lfs, "Fairshare": fair}
            table = self.create_table(columns, user_to_color=user_to_color)
            return table
        elif user_level:
            columns = {"User": user, "Usage": usage, "LevelFS": lfs, "Fairshare": fair}
            caption_raw = ("Users have essentially the same Fairshare value within a group.")
            caption = textwrap.TextWrapper(width=WIDTH).fill(caption_raw)
            table = self.create_table(columns,
                                      show_zero_usage=True,
                                      vertical_line=True,
                                      indent=tb,
                                      user_to_color=user_to_color,
                                      caption=caption)
            return table
        else:
            columns = {"Account": account,
                       "Shares": shares,
                       "Usage": usage,
                       "LevelFS": lfs,
                       "Fairshare": minmax,
                       "ActiveUsers": users}
            caption_raw = ("In the table above, the minimum and maximum Fairshare "
                           "values of the users within each account are shown. "
                           "Fairshare values are assigned in segments. The users "
                           "within the account with the highest LevelFS are "
                           "assigned the highest Fairshare values. Your Fairshare "
                           "value has a large impact on your queue time.")
            caption = textwrap.TextWrapper(width=WIDTH).fill(caption_raw)
            table = self.create_table(columns,
                                      show_zero_usage=True,
                                      vertical_line=vertical_line,
                                      indent=tb,
                                      accounts_to_color=accounts_to_color,
                                      caption=caption)
            return table


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


    def fairshare_rank(self, fs: str) -> Tuple[str, str, str]:
        """Estimate the rank of the user. One could determine it exactly but
           not so important. Note that the total number of users is used
           instead of the active number of users (where usage > 0)."""
        # TODO: maybe this only applies under total (--) since root (root)
        # it also includes pli but that is expected
        total_users = sum(1 for leaf in self.tree.leaves() if "(--)" not in leaf.identifier)
        if total_users == 0:
            return ("0 of 0", "0", "bottom")
        raw_rank = round(total_users * (1 - float(fs)))
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


    def get_total_shares(self, node_id: str) -> int:
        """Return the total shares of the children of the specified parent node.
           Shares that are non-integers are skipped."""
        total = 0
        for child in self.tree.children(node_id):
            if child.data.raw_shares.isdigit():
                total += int(child.data.raw_shares)
        return total


    # TODO hard-coded level
    def get_dept(self, node_id: str) -> str:
        """Return information about the department of the user."""
        if not self.is_pli(node_id):
            total = self.get_total_shares(node_id)
            dept = self.tree.ancestor(node_id, level=2)
            pct = self.dept_share_as_percentage(int(dept.data.raw_shares), total)
            return f"{dept.data.account}: {dept.data.raw_shares}/{total} or {pct}%"
        return "PLI: 300"


    def get_levelfs_rank(self, node_id: str) -> str:
        """Return the rank of the LevelFS values at the level of the specified
           node."""
        target_fs_raw = self.tree[node_id].data.level_fs  # type: ignore[union-attr]
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
    def format_levelfs(lfs: float, padding: bool = False) -> str:
        """Format a LevelFS value for display."""
        if lfs == float("inf"):
            val, pad = "infinity", "    "
        elif lfs > 99_999_999:
            val, pad = f"{lfs:.2e}", "    "
        elif lfs >= 2.5:
            val, pad = f"{lfs:.0f}", "    "
        elif lfs >= 0.95:
            val, pad = f"{lfs:.1f}", "  "
        elif lfs >= 0.095:
            val, pad = f"{lfs:.1f}", "  "
        elif lfs >= 0.0095:
            val, pad = f"{lfs:.2f}", " "
        elif lfs >= 0.00095:
            val, pad = f"{lfs:.3f}", ""
        elif lfs > 0:
            val, pad = f"{lfs:.2e}", "   "
        else:
            val, pad = "0", "    "
        return f"{val}{pad}" if padding else val


    def draw_subtree(self, node_id: str, netid: str) -> None:
        """Draw the subtree from root to the specified node."""
        path = list(self.tree.rsearch(node_id))
        path.reverse()
        tree = Tree()
        tree.create_node(tag=path[0].split()[0], identifier=path[0])
        parent = path[0]
        term = Terminal()
        user = f"{term.bold}{netid}{term.normal}"
        # TODO how to get right node for next line
        #total_shares = self.get_total_shares(node_id)
        for i, p in enumerate(path[1:]):
            rank = self.get_levelfs_rank(p)
            # TODO added strip
            level = self.format_levelfs(float(self.tree[p].data.level_fs)).strip()
            #shares = self.tree[p].data.raw_shares
            if i == 0:
                tree.create_node(tag=f"{p.split()[0]}", identifier=p, parent=parent)
            elif i + 1 == len(path[1:]):
                tree.create_node(tag=f"{user} (LevelFS: {level}, LevelFS Rank: {rank})", identifier=p, parent=parent)
            elif i == 1:
                # TODO
                #tree.create_node(tag=f"{p.split()[0]} (LevelFS: {level}, LevelFS Rank: {rank}, Shares: {shares}/{total_shares})", identifier=p, parent=parent)
                tree.create_node(tag=f"{p.split()[0]} (LevelFS: {level}, LevelFS Rank: {rank})", identifier=p, parent=parent)
            else:
                tree.create_node(tag=f"{p.split()[0]} (LevelFS: {level}, LevelFS Rank: {rank})", identifier=p, parent=parent)
            parent = p
        tree.show()


    @staticmethod
    def colorize(txt: Union[str, int, float], style: str="normal", color: str="black") -> str:
        term = Terminal()
        if not blessed_is_available:
            return str(txt)
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
    def format_fairshare_line(fs: str) -> str:
        """Format and colorize the fairshare value."""
        fs_str = f"{float(fs):{f'.{c.FAIRSHARE_DIGITS}f'}}"
        padding = " " * ((WIDTH - len(fs_str) - len("Fairshare: ")) // 2)
        if float(fs) >= 0.75:
            color = "green"
        elif float(fs) <= 0.28:
            color = "red"
        else:
            color = "black"
        fs_color = ShareTree.colorize(fs_str, style="bold", color=color)
        label = ShareTree.colorize("Fairshare:", style="bold", color="black")
        return f"{padding}{label} {fs_color}"


    @staticmethod
    def format_fairshare(fs: Union[float, str]) -> str:
        """Return fairshare value with appropriate precision."""
        if fs == "--":
            return fs
        return f"{float(fs):{f'.{c.FAIRSHARE_DIGITS}f'}}"


    def explain(self, fs_str: str) -> str:
        """Return an explain of the fairshare of the user and what they can
           expect for queue times."""
        rank, pct, direction = self.fairshare_rank(fs_str)
        wrapper = textwrap.TextWrapper(width=WIDTH)
        fs = float(fs_str)
        if fs >= 0.75:
            msg = (f"Good news! Your fairshare "
                   f"rank is {rank} users which puts you in the {direction} {pct} percentile. "
                  "You should expect relatively short queue times for small to intermediate size jobs.")
        elif fs >= 0.25 and fs < 0.75:
            msg = (f"Your fairshare rank is {rank} users which puts you in the {direction} {pct} percentile. "
                   "You should expect intermediate to long queue times.")
        elif fs >= 0.0 and fs < 0.25:
            msg = (f"Bad news! Your fairshare "
                   f"rank is {rank} users which puts you in the {direction} {pct} percentile. You should expect "
                   "long queue times. The tree at the top helps explain why your fairshare is low.")
        # Fairshare varies between 0 to 1. The larger the value the larger the contribution to job priority
        return wrapper.fill(msg)


    def valid_accounts(self,
                       invalid_account: str,
                       skip_root: Tuple[Tuple[str, ...], ...] = (),
                       width: int = 80) -> str:
        """Return a comma-separated list of valid accounts to be displayed if
           the user supplies an invalid account."""
        accounts: List[str] = []
        if skip_root:
            for path in skip_root:
                node_id = f"{path[-1]} (--)"
                if node_id in self.tree:
                    accounts.extend(child.data.account
                                    for child in self.tree.children(node_id)
                                    if not self.tree[child.identifier].is_leaf())
        else:
            node_id = self.tree.root
            accounts.extend(child.data.account
                            for child in self.tree.children(node_id))

        msg = f'The Slurm account "{invalid_account}" was not found in the sshare tree.'
        if not accounts:
            return msg
        msg += " Below is a list of some of the valid accounts:"
        msg = textwrap.fill(msg, width=width)
        unique_accounts = sorted(set(accounts))
        indent = " " * 4
        txt = textwrap.fill(", ".join(unique_accounts),
                            width=width,
                            initial_indent=indent,
                            subsequent_indent=indent)
        txt += "\n\nFor example:\n"
        txt += f"{indent}$ stree -A {unique_accounts[0]}"
        return f"{msg}\n\n{txt}"
