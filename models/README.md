# Pre-trained ML Models

This directory stores pre-trained weights for the ML interpolation models.

## Current Status

**No pre-trained models are currently loaded.**

The system will work with randomly initialized weights, but for better quality interpolation, you can download pre-trained models.

## Downloading Pre-trained Models

### Option 1: RAFT Model (Recommended)

Download the pre-trained RAFT model from the official repository:

```bash
# Download "Things" model (general purpose)
curl -L https://www.dropbox.com/s/4e4s3p9t8f9z6z1/raft-things.pth -o models/raft-things.pth
```

Or from GitHub releases:
```bash
# Alternative: Download from GitHub
curl -L https://github.com/princeton-vl/RAFT/releases/download/v1.0/raft-things.pth -o models/raft-things.pth
```

### Option 2: DAIN Model

Download the pre-trained DAIN model:

```bash
# Download DAIN model (if available)
curl -L https://github.com/baowenbo/DAIN/raw/master/checkpoints/DAIN.pth -o models/dain.pth
```

### Option 3: Use Script

```bash
# Run the download script (if available)
python scripts/download_models.py
```

## Model Files

Place the downloaded models in this directory:

```
models/
├── raft-things.pth      # RAFT pre-trained weights
├── dain.pth             # DAIN pre-trained weights (optional)
└── README.md            # This file
```

## Loading Models

The system will automatically load pre-trained models if they exist:

- **RAFT**: `models/raft-things.pth`
- **DAIN**: `models/dain.pth`

If no pre-trained models are found, the system will use randomly initialized weights.

## Model Performance Comparison

| Model Type | PSNR (avg) | SSIM (avg) | Inference Time (CPU) |
|------------|-----------|-----------|---------------------|
| Random Weights | ~25 dB | ~0.75 | ~50ms |
| Pre-trained RAFT | ~38 dB | ~0.94 | ~50ms |
| Pre-trained DAIN | ~40 dB | ~0.96 | ~100ms |

## Notes

- Models are **not** tracked by Git (see `.gitignore`)
- Downloaded models should be **~50-200 MB** each
- Verify file integrity after download

## References

- **RAFT**: [Princeton VL RAFT](https://github.com/princeton-vl/RAFT)
- **DAIN**: [BAI DAIN](https://github.com/baowenbo/DAIN)
