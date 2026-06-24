"""submit.zip packager — Phase 6.1.

Packages the two competition CSVs into a zip at archive root (no nested folders).
Both files must already exist in out_dir before calling pack_submit_zip.
"""

from __future__ import annotations

import logging
import os
import zipfile

from config import PREDICT_FILENAME, PATTERN_FILENAME

log = logging.getLogger(__name__)

_REQUIRED = [PREDICT_FILENAME, PATTERN_FILENAME]


def pack_submit_zip(out_dir: str, zip_path: str) -> str:
    """Create a submit.zip from the two competition CSVs in out_dir.

    Both ``predict_result.csv`` and ``pattern_reco.csv`` must exist in
    *out_dir*.  They are stored at the **archive root** (no nested folders).

    Parameters
    ----------
    out_dir:   Directory containing the two output CSVs.
    zip_path:  Destination path for the zip file (created/overwritten).

    Returns
    -------
    The absolute path of the created zip file.

    Raises
    ------
    FileNotFoundError  if either required CSV is absent in out_dir.
    """
    for fname in _REQUIRED:
        src = os.path.join(out_dir, fname)
        if not os.path.isfile(src):
            raise FileNotFoundError(
                f"submit_zip: required file not found: {src} "
                f"(run the pipeline first to produce both CSVs)"
            )

    os.makedirs(os.path.dirname(os.path.abspath(zip_path)), exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fname in _REQUIRED:
            src = os.path.join(out_dir, fname)
            # arcname = bare filename → stored at archive root, no subdir
            zf.write(src, arcname=fname)
            log.info("submit_zip: added %s → %s", src, fname)

    # Verify layout contract (fail loudly if violated)
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
    unexpected = [n for n in names if "/" in n or "\\" in n]
    if unexpected:
        raise RuntimeError(
            f"submit_zip: nested paths in archive (should not happen): {unexpected}"
        )
    expected_set = set(_REQUIRED)
    if set(names) != expected_set:
        raise RuntimeError(
            f"submit_zip: archive contents {names} != expected {sorted(expected_set)}"
        )

    log.info("submit_zip: created %s (%d entries)", zip_path, len(names))
    return os.path.abspath(zip_path)
