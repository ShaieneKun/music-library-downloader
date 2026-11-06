"""Per-cycle summary written at the end of each run log."""
import os
from dataclasses import dataclass, field


@dataclass
class CycleReport:
    download_dir: str = ""
    drive_enabled: bool = False
    drive_songs_path: str = ""
    drive_logs_path: str = ""
    log_file: str = ""
    playlist_total: int = 0
    already_downloaded: list = field(default_factory=list)  # video ids
    to_download: list = field(default_factory=list)         # video ids
    downloaded: list = field(default_factory=list)          # file names
    download_failed: list = field(default_factory=list)     # video ids
    uploaded: list = field(default_factory=list)            # file names
    upload_failed: list = field(default_factory=list)       # file names
    errors: int = 0

    @property
    def had_activity(self):
        return bool(self.to_download or self.uploaded or self.upload_failed
                    or self.errors)

    def render(self):
        def lst(items):
            return "".join(f"\n      - {i}" for i in items) if items else ""

        lines = [
            "=" * 60,
            "CYCLE SUMMARY",
            "=" * 60,
            f"Download directory (full path): {os.path.abspath(self.download_dir)}",
            f"Playlist songs found:           {self.playlist_total}",
            f"Already downloaded (skipped):   {len(self.already_downloaded)}",
            f"To be downloaded:               {len(self.to_download)}"
            + lst(self.to_download),
            f"Actually downloaded:            {len(self.downloaded)}"
            + lst(self.downloaded),
        ]
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
