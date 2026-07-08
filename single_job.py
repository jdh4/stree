import subprocess


class SingleJobBreakdown:

    def __init__(self, user: str, fairshare: float) -> None:
        self.user = user
        self.fairshare = fairshare
        self.num_jobs = 0
        self.job_dict = dict()

    def get_job_data(self) -> None:
        #fmt = "Account,User,RawShares,NormShares,RawUsage,EffectvUsage,FairShare,LevelFS"
        cmd = f"sprio -u {self.user} -S 'Y'"
        output = subprocess.run(cmd,
                                stdout=subprocess.PIPE,
                                encoding="utf8",
                                check=True,
                                text=True,
                                shell=True,
                                timeout=30)
        self.lines = output.stdout.splitlines()

    def parse(self):
        self.num_jobs = len(self.lines) - 1
        if self.num_jobs > 0:
            heading = self.lines[0].split()
            job = self.lines[-1].split()
            self.job_dict = dict(zip(heading, job))

    def explain(self):
        # need to connect partition to the particular slurm account of the user (pli vs. other)
        # need to also call "sprio -w"
        print("Why is your fairshare value important?")
        print("Let's look at your current highest priority job.")
        print("USER  JOBID  QOS  AGE  JOBSIZE")
        print(f'{self.job_dict["USER"]} {self.job_dict["JOBID"]} {self.job_dict["QOS"]} {self.job_dict["AGE"]} {self.job_dict["JOBSIZE"]}\n')
        print("Job priority is calculated as a weighted sum:\n")
        print("   priority = w_a * AGE + w_q * QOS + w_j * JOBSIZE + w_f * FAIRSHARE")
        print(f"   priority = w_a * AGE + w_q * QOS + w_j * JOBSIZE + 12000 * {self.fairshare}")
        print(f"   priority = w_a * AGE + w_q * QOS + w_j * JOBSIZE + {round(12000 * self.fairshare)}")
        print("")
