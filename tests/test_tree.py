import pytest
from sharetree import ShareTree

TEST2 = """root                                          0.000000 184107262492      1.000000
 root                      root          1    0.000081           0      0.000000   1.000000        inf
 pli                                   300    0.024331  6757869864      0.036706              0.662856
  llm                    ab4197          1    0.005025   250122644      0.037012   0.002471   0.135770
 cbe                                   300    0.024331  6757869864      0.036706              0.662856
  mawebb                   jdh4          1    0.005025           0      0.000000   0.079247        inf
  jack                    jdack          1    0.005025           0      0.000000   0.079247        inf"""

TEST = """root                                          0.000000 184107262492      1.000000
 root                      root          1    0.000081           0      0.000000   1.000000        inf
 pli                                   300    0.024331  6757869864      0.036706              0.662856
  pli                    aa6469          1    0.005025           0      0.000000   0.068225 5.0137e+10
  pli                    ab4197          1    0.005025   250122644      0.037012   0.002471   0.135770
  pli                    ac2603          1    0.005025           0      0.000000   0.079247        inf
  pli                    zy6438          1    0.005025           0      0.000000   0.070315 1.4458e+11
  pli                    zy7019          1    0.005025     5208750      0.000771   0.026606   6.519634
  pli                    zzhong          1    0.005025           0      0.000000   0.072976 3.4845e+13
  1kd_hasson_lab                         1    0.005025     5196541      0.000769              6.534951
   1kd_hasson_lab        at3549          1    0.500000     5164711      0.993875   0.026986   0.503082
   1kd_hasson_lab        hr7485          1    0.500000       31830      0.006125   0.027176  81.628773
  adams_group                            1    0.005025       73184      0.000011            464.020070
   adams_group           ag5008          1    0.200000        9576      0.130849   0.045230   1.528475
   adams_group           dn0598          1    0.200000       25456      0.347845   0.045040   0.574968
   adams_group           jaduol          1    0.200000           0      0.000000   0.045800        inf
   adams_group              rpa          1    0.200000           0      0.000000   0.045800        inf
   adams_group           st4629          1    0.200000           0      0.000000   0.045800        inf
  adaptiveopt                            1    0.005025           0      0.000000            2.5864e+08
   adaptiveopt           ak4605          1    0.333333           0      1.000000   0.058913   0.333333
   adaptiveopt             chij          1    0.333333           0      0.000000   0.059293        inf
   adaptiveopt           zt6264          1    0.333333           0      0.000000   0.059293        inf
 total                               12029    0.975588 177372499541      0.963298              1.012759
  aos                                    1    0.000101    89317259      0.000504              0.201510
   cdeutsch                              1    0.250000    89317259      1.000000              0.250000
    cdeutsch             am9753          1    0.090909           0      0.000000   0.423983        inf
    cdeutsch           cdeutsch          1    0.090909     1003327      0.011233   0.422463   8.092824
    cdeutsch             eh9164          1    0.090909           0      0.000000   0.423983        inf
    cdeutsch             yl4399          1    0.090909    77902528      0.872200   0.422083   0.104230
   griffies                              1    0.250000           0      0.000000                   inf
    griffies             cd7350          1    0.166667           0      0.000000   0.426074        inf
    griffies            graemem          1    0.166667           0      0.000000   0.426074        inf
    griffies           krasting          1    0.166667           0      0.000000   0.426074        inf
    griffies                smg          1    0.166667           0      0.000000   0.426074        inf
   jls                                   1    0.250000           0      0.000000                   inf
    jls                     jls          1    0.333333           0      0.000000   0.426074        inf
    jls                mmazloff          1    0.333333           0      0.000000   0.426074        inf
    jls                    ss23          1    0.333333           0      0.000000   0.426074        inf
   krodgers                              1    0.250000           0      0.000000                   inf
    krodgers           krodgers          1    0.500000           0      0.000000   0.426074        inf
    krodgers           rdslater          1    0.500000           0      0.000000   0.426074        inf
  architecture                           1    0.000101     1258747      0.000007             14.298399
   arashadel                             1    1.000000     1258747      1.000000              1.000000
    arashadel            aa9663          1    0.200000           0      0.000000   0.996579        inf
    arashadel            dr5390          1    0.200000        2456      0.001951   0.996389 102.499822
    arashadel            jg8685          1    0.200000     1235042      0.981168   0.995819   0.203839
    arashadel            ri1129          1    0.200000        6361      0.005054   0.996199  39.573174
    arashadel            sm6489          1    0.200000       14886      0.011826   0.996009  16.911379
  astro                                 11    0.001116  3634265676      0.020494              0.054476
   aamon                                 1    0.050000     3673043      0.001011             49.472129"""


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


def test_simple_example(small_tree):
    t = ShareTree()
    t.get_raw_data(text=small_tree)
    t.parse("aturing")
    assert len(t.tree.leaves()) == 4


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
    """Test for one association."""
    t = ShareTree()
    sshare = ("root 1 2 3\n"
              " cbe 1 2 3 4 55.0\n"
              "  pi1 u1 1 2 3 4 5 6\n")
    t.get_raw_data(text=sshare)
    t.parse("aturing")
    assert t.get_levelfs_rank("cbe (--)") == "1/1"


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


def test_get_total_shares(small_tree):
    t = ShareTree()
    t.get_raw_data(text=small_tree)
    t.parse("aturing")
    assert t.get_total_shares() == 42
    assert t.get_total_shares("total (--)") == 42
    assert t.get_total_shares("pli (--)") == 1
    assert t.get_total_shares("root (--)") == 3
