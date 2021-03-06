"""Script for benchmarking Sorald's performance on a set of repositories."""

import argparse
import sys
import pathlib
import git
import tempfile
import json
import dataclasses
import itertools
import contextlib
import functools

from multiprocessing.pool import ThreadPool
from typing import List, Mapping, Iterable, Tuple, Optional

import pandas as pd
import tqdm

from sorald._helpers import soraldwrapper, jsonkeys

SINGLE_RUN_TIMEOUT = 15 * 60


def main(args: List[str]):
    parsed_args = parse_args(args)
    commits_to_analyze = read_commits_csv(parsed_args)

    results = list(
        benchmark_commits(
            commits_to_analyze, parsed_args.rule_keys, parsed_args.parallel_experiments
        )
    )

    results_frame = convert_results_to_dataframe(results)
    results_frame.to_csv(parsed_args.output, index=False)

    if parsed_args.compare and performance_has_deteriorated(
        commits_to_analyze, results_frame
    ):
        sys.exit(1)
    if any(res.crash for res in results):
        crash_str = "\n".join([res.commit_id for res in results if res.crash])
        print(f"Some repairs crashed: \n{crash_str}", file=sys.stderr)
        sys.exit(1)


def parse_args(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=f"{__package__}.{pathlib.Path(__file__).name[:-3]}",
        description="Benchmark script for evaluating Sorald's performance.",
    )
    parser.add_argument(
        "--commits-csv",
        help="path to a csv file with commits, at least containing the column "
        "headers 'url' and 'commit'",
        required=True,
        type=pathlib.Path,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="path to the output CSV file",
        required=True,
        type=pathlib.Path,
    )
    parser.add_argument(
        "-c",
        "--compare",
        help="use the input data to compare with the benchmark results. "
        f"Requires all column headers the commits file: {STATS_COLUMNS}",
        action="store_true",
    )
    parser.add_argument(
        "-p",
        "--parallel-experiments",
        help="amount of experiments to run in parallel",
        type=int,
        default=1,
    )
    parser.add_argument(
        "-r",
        "--rule-keys",
        nargs="*",
        help="rule keys to use. If not specified, all rule keys are used.",
        default=soraldwrapper.available_rule_keys(),
    )

    return parser.parse_args(args)


def read_commits_csv(parsed_args: argparse.Namespace) -> pd.DataFrame:
    commits_to_analyze = pd.read_csv(parsed_args.commits_csv)
    if "rule_key" in commits_to_analyze.columns.values:
        commits_to_analyze = commits_to_analyze.astype({"rule_key": str})

    input_columns = list(commits_to_analyze.columns.array)
    if parsed_args.compare and input_columns != STATS_COLUMNS:
        raise RuntimeError(
            f"Cannot compare with input data, expected columns {STATS_COLUMNS} "
            f"but found {input_columns}"
        )

    return commits_to_analyze


def convert_results_to_dataframe(
    results: List["CommitRepairStats"],
) -> pd.DataFrame:
    results_iter = iter(results)
    first_result = next(results_iter)
    results_frame = pd.DataFrame(
        columns=STATS_COLUMNS, data=first_result.to_results_tuples()
    )

    for commit_stats in results_iter:
        for rs in commit_stats.to_results_tuples():
            results_frame.loc[len(results_frame)] = rs

    results_frame = results_frame.sort_values(
        by=["url", "commit", "rule_key"],
    ).reset_index(drop=True)

    return results_frame


def performance_has_deteriorated(
    old_results: pd.DataFrame, new_results: pd.DataFrame
) -> bool:
    """Returns True iff performance has deteriorated."""
    diff = pd.concat([old_results, new_results]).drop_duplicates(keep=False)
    if len(diff) == 0:
        print("Old and new results match exactly")
        return False
    else:
        print("Old and new results differ on the following commits: ")
        print(diff[["url", "commit"]].drop_duplicates(keep="first"))

    deteriorated = False
    old_num_successful_repairs = old_results.num_successful_repairs.sum()
    new_num_successful_repairs = new_results.num_successful_repairs.sum()
    old_total_repair_ratio = (
        old_num_successful_repairs / old_results.num_violations_before.sum()
    )
    new_total_repair_ratio = (
        new_num_successful_repairs / new_results.num_violations_before.sum()
    )

    print()
    print(f"Old total_repair_ratio: {old_total_repair_ratio}")
    print(f"New total_repair_ratio: {new_total_repair_ratio}")

    if new_total_repair_ratio < old_total_repair_ratio:
        print("total_repair_ratio has deteriorated")
        deteriorated = True
    else:
        print("total_repair_ratio is unchanged or improved")

    old_attempted_repair_ratio = (
        old_num_successful_repairs / old_results.num_performed_repairs.sum()
    )
    new_attempted_repair_ratio = (
        new_num_successful_repairs / new_results.num_performed_repairs.sum()
    )

    print()
    print(f"Old attempted_repair_ratio: {old_attempted_repair_ratio}")
    print(f"New attempted_repair_ratio: {new_attempted_repair_ratio}")

    if new_attempted_repair_ratio < old_attempted_repair_ratio:
        print("attempted_repair_ratio has deteriorated")
        deteriorated = True
    else:
        print("attempted_repair_ratio is unchanged or improved")

    return deteriorated


def benchmark_commits(
    commits_to_analyze: pd.DataFrame,
    rule_keys: List[str],
    num_parallel_experiments: int,
) -> Iterable["CommitRepairStats"]:
    pool = ThreadPool(num_parallel_experiments)
    unique_commits = commits_to_analyze[["url", "commit"]].drop_duplicates(
        keep="first", ignore_index=True
    )
    args = [(row.url, row.commit, rule_keys) for _, row in unique_commits.iterrows()]
    results = pool.imap(imappable_benchmark_commit, args)
    results_progress = tqdm.tqdm(
        results, desc="Processing commits", total=len(unique_commits)
    )

    for result in results_progress:
        results_progress.write(f"Processed {result.commit_id}")
        yield result


def imappable_benchmark_commit(tup: Tuple[str, str, List[str]]) -> "CommitRepairStats":
    return benchmark_commit(*tup)


def benchmark_commit(
    url: str, commit: str, rule_keys: List[str]
) -> "CommitRepairStats":
    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = pathlib.Path(tmpdir)
        repo = git.Repo.clone_from(url, to_path=workdir)
        repo.git.checkout(commit)
        repo_repair_stats = _benchmark_commit(repo, rule_keys)

    return repo_repair_stats


def _benchmark_commit(repo: git.Repo, rule_keys: List[str]) -> "CommitRepairStats":
    repair_stats = list(map(functools.partial(run_sorald_for_rule, repo), rule_keys))

    return CommitRepairStats(
        project_url=next(repo.remote().urls),
        commit_sha=repo.head.commit.hexsha,
        repair_stats=repair_stats,
    )


def run_sorald_for_rule(repo: git.Repo, rule_key: str) -> "RepairStats":
    workdir = pathlib.Path(repo.working_dir)
    stats_file = workdir / "stats.json"

    with restore_head_after(repo):
        return_code, *_ = soraldwrapper.sorald(
            "repair",
            source=pathlib.Path(repo.working_dir),
            stats_output_file=workdir / stats_file,
            rule_key=rule_key,
            timeout=SINGLE_RUN_TIMEOUT,
        )
        if return_code != 0:
            print(
                f"Failed to process {commit_id(repo)} with key {rule_key}",
                file=sys.stderr,
            )
            return RepairStats.empty(rule_key, crash=True)

        repair_dicts = json.loads(stats_file.read_text(encoding="utf8"))[
            jsonkeys.SORALD_STATS.REPAIRS
        ]

    assert len(repair_dicts) <= 1, "Unexpected amount of repair statistics"

    return (
        RepairStats.empty(rule_key, crash=False)
        if not repair_dicts
        else RepairStats.from_repair_dict(repair_dicts[0])
    )


def commit_id(repo: git.Repo) -> str:
    return f"{next(repo.remote().urls)}@{repo.head.commit.hexsha}"


@contextlib.contextmanager
def restore_head_after(repo: git.Repo):
    head = repo.head.commit.hexsha
    yield
    repo.git.checkout(head, "--force")
    repo.git.clean("-xfd")


@dataclasses.dataclass(frozen=True)
class RepairStats:
    """Statistics for a single repair."""

    rule_key: str
    crash: bool
    num_violations_before: int
    num_violations_after: int
    num_performed_repairs: int
    num_crashed_repairs: int
    num_successful_repairs: int
    num_failed_repairs: int

    @staticmethod
    def from_repair_dict(repair: dict) -> "RepairStats":
        stat_keys = jsonkeys.SORALD_STATS

        num_violations_before = repair[stat_keys.VIOLATIONS_BEFORE]
        num_violations_after = repair[stat_keys.VIOLATIONS_AFTER]
        num_performed_repairs = repair[stat_keys.NUM_PERFORMED_REPAIRS]

        num_successful_repairs = num_violations_before - num_violations_after
        num_failed_repairs = num_performed_repairs - num_successful_repairs
        return RepairStats(
            rule_key=repair[stat_keys.RULE_KEY],
            num_violations_before=num_violations_before,
            num_violations_after=num_violations_after,
            num_performed_repairs=num_performed_repairs,
            num_crashed_repairs=repair[stat_keys.NUM_CRASHED_REPAIRS],
            num_successful_repairs=num_successful_repairs,
            num_failed_repairs=num_failed_repairs,
            crash=False,
        )

    @staticmethod
    def empty(rule_key: str, crash: bool) -> "RepairStats":
        zeros = [0] * (len(dataclasses.fields(RepairStats)) - 2)
        return RepairStats(rule_key, crash, *zeros)


STATS_COLUMNS = [
    "url",
    "commit",
    *[f.name for f in dataclasses.fields(RepairStats)],
]


@dataclasses.dataclass(frozen=True)
class CommitRepairStats:
    project_url: str
    commit_sha: str
    repair_stats: List[RepairStats]

    @property
    def commit_id(self):
        return f"{self.project_url}@{self.commit_sha}"

    @property
    def crash(self):
        return any(rs.crash for rs in self.repair_stats)

    def to_results_tuples(self) -> List[tuple]:
        return [
            (self.project_url, self.commit_sha, *dataclasses.astuple(rs))
            for rs in self.repair_stats
        ]


if __name__ == "__main__":
    main(sys.argv[1:])
