"""
Git operations for upstream sync.
"""
import subprocess
from pathlib import Path
from dataclasses import dataclass

UPSTREAM_URL = "https://github.com/ntdevlabs/tiny11builder.git"


@dataclass
class GitStatus:
    branch: str
    ahead: int
    behind: int
    dirty: bool
    has_upstream: bool


def _ensure_upstream(repo_dir: Path) -> bool:
    """Ensure upstream remote exists. Auto-add if missing. Returns True if upstream is available."""
    r = subprocess.run(["git", "remote"], cwd=repo_dir, capture_output=True, text=True)
    if "upstream" in r.stdout:
        return True
    # Auto-add upstream
    r = subprocess.run(
        ["git", "remote", "add", "upstream", UPSTREAM_URL],
        cwd=repo_dir, capture_output=True, text=True
    )
    return r.returncode == 0


def get_status(repo_dir: Path) -> GitStatus:
    """Get git status of the repo."""
    def run(cmd: list[str]) -> str:
        r = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True)
        return r.stdout.strip()
    
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    
    # Ensure upstream exists
    has_upstream = _ensure_upstream(repo_dir)
    
    ahead = behind = 0
    if has_upstream:
        # Fetch first
        subprocess.run(["git", "fetch", "upstream"], cwd=repo_dir, capture_output=True)
        # Compare
        local = run(["git", "rev-parse", "HEAD"])
        remote = run(["git", "rev-parse", "upstream/main"])
        if local != remote:
            merge_base = run(["git", "merge-base", "HEAD", "upstream/main"])
            ahead = len(run(["git", "rev-list", f"{merge_base}..HEAD"]).splitlines()) if merge_base else 0
            behind = len(run(["git", "rev-list", f"HEAD..upstream/main"]).splitlines()) if merge_base else 0
    
    dirty = bool(run(["git", "status", "--porcelain"]))
    
    return GitStatus(branch=branch, ahead=ahead, behind=behind, dirty=dirty, has_upstream=has_upstream)


def pull_upstream(repo_dir: Path) -> tuple[bool, str]:
    """Pull from upstream/main. Returns (success, message)."""
    try:
        # Ensure upstream exists
        if not _ensure_upstream(repo_dir):
            return False, "Failed to add upstream remote"
        
        # Fetch
        r = subprocess.run(
            ["git", "fetch", "upstream"],
            cwd=repo_dir, capture_output=True, text=True
        )
        if r.returncode != 0:
            return False, f"Fetch failed: {r.stderr}"
        
        # Merge
        r = subprocess.run(
            ["git", "merge", "upstream/main", "--no-edit"],
            cwd=repo_dir, capture_output=True, text=True
        )
        if r.returncode != 0:
            # Try to abort merge on failure
            subprocess.run(["git", "merge", "--abort"], cwd=repo_dir, capture_output=True)
            return False, f"Merge failed: {r.stderr}\n{r.stdout}"
        
        return True, f"Successfully merged upstream/main\n{r.stdout}"
    except Exception as e:
        return False, str(e)


def get_log(repo_dir: Path, count: int = 20) -> list[dict[str, str]]:
    """Get recent git log."""
    r = subprocess.run(
        ["git", "log", f"-{count}", "--pretty=format:%H|%h|%s|%an|%ai"],
        cwd=repo_dir, capture_output=True, text=True
    )
    entries = []
    for line in r.stdout.strip().splitlines():
        parts = line.split("|", 4)
        if len(parts) == 5:
            entries.append({
                "hash": parts[0],
                "short": parts[1],
                "subject": parts[2],
                "author": parts[3],
                "date": parts[4],
            })
    return entries


def get_diff_summary(repo_dir: Path) -> str:
    """Get a summary of local vs upstream differences."""
    r = subprocess.run(
        ["git", "diff", "--stat", "HEAD", "upstream/main"],
        cwd=repo_dir, capture_output=True, text=True
    )
    return r.stdout.strip()
