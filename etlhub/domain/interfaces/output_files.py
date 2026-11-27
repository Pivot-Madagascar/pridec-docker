from typing import Protocol


class OutputFiles(Protocol):
    """Work files of the mode served, offered for download: the forecast report, input/ and output/ as a zip."""

    def report(self) -> str | None:
        """output/forecast_report.html, None when absent; raises when it cannot be read."""
        ...

    def archive(self, folder: str | None) -> bytes | None:
        """Zip of input/ and output/, or of `folder` only (pass folders and symbolic links left out); None when empty."""
        ...
