import pytest
from sharetree import ShareTree
from treelib.exceptions import DuplicatedNodeIdError


@pytest.fixture
def small_tree():
    sshare = ("root 1.0 2 3.0\n"
              " root root 1 2.0 3 4.0 5.0 6.0\n"
              " total 1 2.0 3 4.0 5.0\n"
              "  chem jdh4 1 2.0 3 4.0 5.0 6.0\n"
              "  orfe jdh4 41 2.0 3 4.0 5.0 6.0\n"
              " pli 1 2.0 3 4.0 5.0\n"
              "  pli jdh4 1 2.0 3 4.0 5.0 6.0\n")
    return sshare


@pytest.fixture
def medium_tree():
    sshare = ("root 1.0 2 3.0\n"
              " root root 1 2.0 3 4.0 5.0 6.0\n"
              " total 1 2.0 3 4.0 5.0\n"
              "  chem 1 2.0 3 4.0 0.5\n"
              "   rcar 1 2.0 3 4.0 0.5\n"
              "    rcar u1 1 2.0 3 4.0 5.0 0.6\n"
              "    rcar u2 1 2.0 3 4.0 5.0 6.0\n"
              "   soos 1 2.0 3 4.0 5.0\n"
              "    soos u1 1 2.0 3 4.0 5.0 6.0\n"
              "    soos u2 1 2.0 3 4.0 5.0 6.0\n"
              "  orfe 1 2.0 3 4.0 5.0\n"
              "   kent 1 2.0 3 4.0 5.0\n"
              "    kent u1 1 2.0 3 4.0 5.0 6.0\n"
              "    kent u2 1 2.0 3 4.0 5.0 inf\n"
              "    kent u3 1 2.0 3 4.0 5.0 0.6\n"
              "    kent u4 1 2.0 3 4.0 5.0 inf\n"
              " pli 1 2.0 3 4.0 5.0\n"
              "  pli u1 1 2.0 3 4.0 5.0 6.0\n")
    return sshare


@pytest.fixture
def deep_tree():
    sshare = ("root 1.0 2 3.0\n"
              " root root 1 2.0 3 4.0 5.0 6.0\n"
              " total 1 2.0 3 4.0 5.0\n"
              "  chem 1 2.0 3 4.0 0.5\n"
              "   rcar 1 2.0 3 4.0 0.5\n"
              "    soos 1 2.0 3 4.0 5.0\n"
              "     benz 1 2.0 3 4.0 5.0\n"
              "      benz u1 1 2.0 3 4.0 5.0 6.0\n"
              "      benz u2 1 2.0 3 4.0 0.5 6.0\n"
              "  orfe 1 2.0 3 4.0 5.0\n"
              "   kent 1 2.0 3 4.0 5.0\n"
              "    kent u1 1 2.0 3 4.0 5.5 6.0\n"
              " cft 1 2.0 3 4.0 5.0\n"
              " pli 1 2.0 3 4.0 5.0\n"
              "  pli u1 1 2.0 3 4.0 5.0 6.0\n"
              "  pli u2 1 2.0 3 4.0 5.0 6.0\n"
              "  llm 1 2.0 3 4.0 5.0\n"
              "   tom u1 1 2.0 3 4.0 5.0 inf\n")
    return sshare


def test_simple_example(small_tree):
    t = ShareTree()
    t.get_raw_data(text=small_tree)
    t.parse("aturing")
    assert t.tree.size() == 7
    assert t.tree.depth() == 2
    assert len(t.tree.leaves()) == 4
    expected = ["chem (jdh4)", "orfe (jdh4)"]
    assert [child.identifier for child in t.tree.children("total (--)")] == expected
    assert t.tree.level("total (--)") == 1
    assert t.tree["orfe (jdh4)"].data.level_fs == "6.0"


def test_simple_example_med(medium_tree):
    t = ShareTree()
    t.get_raw_data(text=medium_tree)
    t.parse("aturing")
    assert t.tree.size() == 18
    assert t.tree.depth() == 4
    assert len(t.tree.leaves()) == 10
    expected = ["chem (--)", "orfe (--)"]
    assert [child.identifier for child in t.tree.children("total (--)")] == expected
    expected = ["soos (u1)", "soos (u2)"]
    assert [child.identifier for child in t.tree.children("soos (--)")] == expected
    assert t.tree["pli (u1)"].data.fair_share == "5.0"
    expected = ["kent (u4)", "kent (--)", "orfe (--)", "total (--)", "root (--)"]
    assert list(t.tree.rsearch("kent (u4)")) == expected
    assert t.tree["kent (u3)"].data.raw_usage == "3"


def test_simple_example_deep(deep_tree):
    t = ShareTree()
    t.get_raw_data(text=deep_tree)
    t.parse("aturing")
    assert t.tree.size() == 18
    assert t.tree.depth() == 6
    assert len(t.tree.leaves()) == 8
    expected = ["chem (--)", "orfe (--)"]
    assert [child.identifier for child in t.tree.children("total (--)")] == expected
    expected = ["benz (u1)", "benz (u2)"]
    assert [child.identifier for child in t.tree.children("benz (--)")] == expected
    expected = ["benz (u2)", "benz (--)", "soos (--)", "rcar (--)", "chem (--)", "total (--)", "root (--)"]
    assert list(t.tree.rsearch("benz (u2)")) == expected
    assert t.tree["tom (u1)"].data.level_fs == "inf"


def test_duplication_association():
    with pytest.raises(DuplicatedNodeIdError):
        t = ShareTree()
        sshare = ("root 1.0 2 3.0\n"
                  " root root 1 2.0 3 4.0 5.0 6.0\n"
                  " root root 1 2.0 3 4.0 5.0 6.0\n")
        t.get_raw_data(text=sshare)
        t.parse("aturing")


def test_parse_count():
    with pytest.raises(ValueError):
        t = ShareTree()
        sshare = ("root 1.0 2 3.0\n"
                  " root root 1 2.0 3 4.0 5.0\n")
        t.get_raw_data(text=sshare)
        t.parse("aturing")


def test_get_levelfs_rank():
    t = ShareTree()
    sshare = ("root 1 2 3\n"
              " cbe 1 2 3 4 55.0\n"
              "  pi1 u1 1 2 3 4 5 6\n"
              " lsi 1 2 3 4 0.5\n"
              "  pi2 u2 1 2 3 4 5 6\n"
              " mae 1 2 3 4 inf\n"
              "  pi3 u3 1 2 3 4 5 6\n"
              " pni 1 2 3 4 inf\n"
              "  pi4 u4 1 2 3 4 5 6\n"
              "  pi5 u5 1 2 3 4 5 6\n")
    t.get_raw_data(text=sshare)
    t.parse("aturing")
    assert t.get_levelfs_rank("cbe (--)") == "3/4"
    assert t.get_levelfs_rank("lsi (--)") == "4/4"
    assert t.get_levelfs_rank("mae (--)") == "1/4"
    assert t.get_levelfs_rank("pni (--)") == "1/4"
    # test for one association
    t = ShareTree()
    sshare = ("root 1 2 3\n"
              " cbe 1 2 3 4 55.0\n"
              "  pi1 u1 1 2 3 4 5 6\n")
    t.get_raw_data(text=sshare)
    t.parse("aturing")
    assert t.get_levelfs_rank("cbe (--)") == "1/1"


def test_get_levelfs_rank_med(medium_tree):
    t = ShareTree()
    t.get_raw_data(text=medium_tree)
    t.parse("aturing")
    assert t.get_levelfs_rank("chem (--)") == "2/2"
    assert t.get_levelfs_rank("orfe (--)") == "1/2"
    assert t.get_levelfs_rank("rcar (u1)") == "2/2"
    assert t.get_levelfs_rank("rcar (u2)") == "1/2"
    # check for no siblings
    assert t.get_levelfs_rank("kent (--)") == "1/1"
    # check for handling of inf
    assert t.get_levelfs_rank("kent (u1)") == "3/4"
    assert t.get_levelfs_rank("kent (u2)") == "1/4"
    assert t.get_levelfs_rank("kent (u3)") == "4/4"
    assert t.get_levelfs_rank("kent (u4)") == "1/4"


def test_add_proportions():
    t = ShareTree()
    shares = []
    assert t.add_proportions(shares) == []
    shares = ["25"]
    assert t.add_proportions(shares) == ["25 (100%)"]
    shares = ["50", "20", "5", "25"]
    expected = ["50 (50%)", "20 (20%)", "5  (5%)", "25 (25%)"]
    assert t.add_proportions(shares) == expected
    shares = ["49", "14", "1", "119"]
    expected = ["49 (26.8%)", "14  (7.7%)", "1  (0.5%)", "119 (65.0%)"]
    assert t.add_proportions(shares, decimals=1) == expected
    shares = ["49", "14", "1", "119"]
    expected = ["49 (26.78%)", "14  (7.65%)", "1  (0.55%)", "119 (65.03%)"]
    assert t.add_proportions(shares, decimals=2) == expected
    shares = ["49", "49"]
    expected = ["49 (50.00%)", "49 (50.00%)"]
    assert t.add_proportions(shares, decimals=2) == expected


def test_format_levelfs():
    t = ShareTree()
    assert t.format_levelfs(1.1) == "1"
    assert t.format_levelfs(0.1) == "0.1"
    assert t.format_levelfs(0.10) == "0.1"
    assert t.format_levelfs(0.042) == "0.04"
    assert t.format_levelfs(0.0042) == "0.004"
    assert t.format_levelfs(123.456) == "123"
    assert t.format_levelfs(float("inf")) == "infinity"
    assert t.format_levelfs(1.234e+03) == "1234"
    assert t.format_levelfs(1.234e+12) == "1.23e+12"
    assert t.format_levelfs(0.0095) == "0.009"
    assert t.format_levelfs(1.234e-06) == "1.23e-06"


def test_format_percentile():
    t = ShareTree()
    assert t.format_percentile(100) == "100th"
    assert t.format_percentile(78) == "78th"
    assert t.format_percentile(53) == "53rd"
    assert t.format_percentile(42) == "42nd"
    assert t.format_percentile(21) == "21st"
    assert t.format_percentile(0) == "0th"


def test_get_total_shares(small_tree):
    t = ShareTree()
    t.get_raw_data(text=small_tree)
    t.parse("aturing")
    assert t.get_total_shares() == 42
    assert t.get_total_shares("total (--)") == 42
    assert t.get_total_shares("pli (--)") == 1
    assert t.get_total_shares("root (--)") == 3


def test_get_total_shares_med(medium_tree):
    t = ShareTree()
    t.get_raw_data(text=medium_tree)
    t.parse("aturing")
    assert t.get_total_shares() == 2
    assert t.get_total_shares("total (--)") == 2
    assert t.get_total_shares("kent (--)") == 4


def test_fairshare_rank(medium_tree):
    t = ShareTree()
    t.get_raw_data(text=medium_tree)
    t.parse("aturing")
    assert t.fairshare_rank(1.0) == ("1 of 10", "100th", "top")
    assert t.fairshare_rank(0.75) == ("2 of 10", "80th", "top")
    assert t.fairshare_rank(0.5) == ("5 of 10", "50th", "top")
    assert t.fairshare_rank(0.25) == ("8 of 10", "20th", "bottom")
    assert t.fairshare_rank(0.0) == ("10 of 10", "0th", "bottom")


def test_number_of_active_users():
    # usage is numerical column 3
    t = ShareTree()
    sshare = ("root 1.0 2 3.0\n"
              " root root 1 2.0 3 4.0 5.0 6.0\n"
              " total 1 2.0 3 4.0 5.0\n"
              "  chem u1 1 2.0 3 4.0 5.0 6.0\n"
              "  orfe u2 1 2.0 0 4.0 5.0 6.0\n"
              "  shop u3 1 2.0 0 4.0 5.0 6.0\n"
              "  ai 1 2.0 3 4.0 5.0\n"
              " pli 1 2.0 3 4.0 5.0\n"
              "  pli u4 1 2.0 3 4.0 5.0 6.0\n"
              "  llm 1 2.0 3 4.0 5.0\n"
              "   rdr u5 1 2.0 3 4.0 5.0 6.0\n")
    t.get_raw_data(text=sshare)
    t.parse("aturing")
    assert t.number_of_active_users("total (--)") == 1
    assert t.number_of_active_users("ai (--)") == 0
    assert t.number_of_active_users("pli (--)") == 2


def test_min_max_fairshare(deep_tree):
    t = ShareTree()
    t.get_raw_data(text=deep_tree)
    t.parse("aturing")
    descendant_node = t.tree["benz (--)"]
    assert t.min_max_fairshare(descendant_node) == ("0.500000", "5.000000")
    descendant_node = t.tree["benz (u2)"]
    assert t.min_max_fairshare(descendant_node) == ("--", "--")
    descendant_node = t.tree["cft (--)"]
    assert t.min_max_fairshare(descendant_node) == ("--", "--")
    descendant_node = t.tree["total (--)"]
    assert t.min_max_fairshare(descendant_node) == ("0.500000", "5.500000")
    descendant_node = t.tree["llm (--)"]
    assert t.min_max_fairshare(descendant_node) == ("5.000000", "5.000000")
