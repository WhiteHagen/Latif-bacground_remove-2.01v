# Patch Report - Latif Background Remover v2.0

## [2026-03-20] - Version 2.0.1 (English Localization & Optimization)

### Added
- **Torch & Torchvision:** Included in `requirements.txt` to ensure full compatibility with `rembg` internal utilities and specific model backends. This also accounts for the expected ~2.33 GB installation footprint.
- **AI Model Pre-download:** Updated both `setup_gui.py` and `LatifSetup.iss` to automatically download and verify all major AI models (`u2net`, `u2netp`, `u2net_human_seg`, `isnet-general-use`, `silueta`) during the installation process.
- **Robustness Checks:** Added explicit Python environment validation in `setup_gui.py` to ensure the installer doesn't fail silently if Python is missing or misconfigured.
- **Metadata Collection:** Updated `.spec` files to ensure all metadata for `rembg`, `pymatting`, and `onnxruntime` is correctly bundled.
- **Real-time Installer Logs:** `setup_gui.py` now streams stdout/stderr from subprocesses (pip, rembg) in real-time to the log window, preventing the UI from freezing and showing download progress.

### Changed
- **Numpy Versioning:** Pinnded `numpy==1.26.4` to maintain compatibility with `onnxruntime` and avoid potential "module not found" or "API mismatch" errors found in newer 2.x versions.
- **Acceleration Backend:** Defaulted to `onnxruntime-directml` for Windows users to provide hardware acceleration (GPU) across a wide range of graphics cards without requiring complex CUDA setups.
- **Installer Permissions:** Configured the installer (`LatifSetup.spec`) to request Administrator privileges (`uac_admin=True`) to ensure it can correctly register files and create folders in protected directories like `C:\Program Files`.
- **Improved AI Download Script:** The download script now reports the status of each model individually and measures the time taken, providing better feedback during the ~500MB+ download phase.

### Fixed
- **Dependency Gaps:** Added missing libraries identified from the Polish version (`PyMatting`, `importlib-metadata`, `scipy`, `scikit-image`) to ensure the English version is functionally identical and fully stable.
- **Environment Linking:** The installer now uses `pip install -r requirements.txt` which is idempotent—it will skip already installed packages but ensure all necessary links and dependencies are correctly "plugged in" for the `app.py` logic.
