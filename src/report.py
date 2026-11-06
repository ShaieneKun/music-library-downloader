"""Per-cycle summary written at the end of each run log."""
import os
from dataclasses import dataclass, field


@dataclass
class CycleReport:
    download_dir: str = ""
    host_download_dir: str = ""  # shown instead of download_dir if set
    drive_enabled: bool = False
    drive_songs_path: str = ""
    drive_logs_path: str = ""
    log_file: str = ""
    playlist_total: int = 0
    already_downloaded: list = field(default_factory=list)  # video ids
    to_download: list = field(default_factory=list)         # video ids
    downloaded: list = field(default_factory=list)          # file names
    download_failed: list = field(default_factory=list)     # video ids
    download_workers: int = None          # parallel download threads
    download_gap_seconds: float = None    # min gap between song starts
    download_retries_allowed: int = None  # max retries per song
    retries: dict = field(default_factory=dict)             # video id -> retries done
    retry_recovered: list = field(default_factory=list)     # retried ids that then succeeded
    uploaded: list = field(default_factory=list)            # file names
    upload_failed: list = field(default_factory=list)       # file names
    errors: int = 0
    hostname: str = ""
    mode: str = "manual"  # "daemon" (run) or "manual" (once and similar)
    daemon_uptime_seconds: float = None  # daemon only
    daemon_cycles: int = None            # daemon only, includes this cycle

    @property
    def had_activity(self):
        return bool(self.to_download or self.uploaded or self.upload_failed
                    or self.errors)

    @staticmethod
    def format_duration(seconds):
        seconds = int(seconds)
        days, rest = divmod(seconds, 86400)
        hours, rest = divmod(rest, 3600)
        minutes, secs = divmod(rest, 60)
        parts = [(days, "d"), (hours, "h"), (minutes, "m")]
        text = " ".join(f"{n}{u}" for n, u in parts if n)
        return f"{text} {secs}s".strip()

    def render(self):
        def lst(items):
            return "".join(f"\n      - {i}" for i in items) if items else ""

        lines = [
            "=" * 60,
            "CYCLE SUMMARY",
            "=" * 60,
            f"Host:                           {self.hostname or '(unknown)'}",
        ]
        if self.mode == "daemon":
            lines.append("Run mode:                       daemon")
            if self.daemon_uptime_seconds is not None:
                lines.append("Daemon running for:             "
                             + self.format_duration(self.daemon_uptime_seconds))
            if self.daemon_cycles is not None:
                lines.append(f"Daemon cycles so far:           {self.daemon_cycles}"
                             " (including this one)")
        else:
            lines.append("Run mode:                       manual (single run)")
        lines += [
            "Download directory (full path): "
            + (self.host_download_dir or os.path.abspath(self.download_dir)),
            f"Playlist songs found:           {self.playlist_total}",
            f"Already downloaded (skipped):   {len(self.already_downloaded)}",
            f"To be downloaded:               {len(self.to_download)}"
            + lst(self.to_download),
            f"Actually downloaded:            {len(self.downloaded)}"
            + lst(self.downloaded),
        ]
        if self.download_workers is not None:
            gap = f"{self.download_gap_seconds:g}s"
            lines += [
                f"Download workers:               {self.download_workers}",
                f"Gap between song starts:        {gap}",
                f"Retries allowed per song:       {self.download_retries_allowed}",
            ]
            total = sum(self.retries.values())
            detail = ""
            if total:
                failed = [i for i in self.retries if i not in self.retry_recovered]
                detail = (f" ({len(self.retry_recovered)} song(s) recovered, "
                          f"{len(failed)} still failed)")
            lines.append(f"Retries done:                   {total}{detail}"
                         + lst(f"{i}: {n} retr{'y' if n == 1 else 'ies'}, "
                               + ("recovered" if i in self.retry_recovered
                                  else "failed")
                               for i, n in self.retries.items()))
        if self.download_failed:
            lines.append(f"Download failed:                {len(self.download_failed)}"
                         + lst(self.download_failed))
        if self.drive_enabled:
            lines += [
                f"Google Drive songs path:        {self.drive_songs_path}",
                f"Uploaded to Google Drive:       {len(self.uploaded)}"
                + lst(self.uploaded),
            ]
            if self.upload_failed:
                lines.append(f"Upload failed:                  {len(self.upload_failed)}"
                             + lst(self.upload_failed))
            lines.append(f"Google Drive logs path:         {self.drive_logs_path}")
        else:
            lines.append("Google Drive upload:            disabled")
        lines += [
            f"Errors logged this cycle:       {self.errors}",
            f"Log file:                       {os.path.abspath(self.log_file)}",
            "=" * 60,
        ]
        return "\n".join(lines)
