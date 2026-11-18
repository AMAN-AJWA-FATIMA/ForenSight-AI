# Dataset selection report (Phase 1)

Verified on 13 Nov 2026 from the public pages listed below. Items marked **to confirm at run time** could not be checked
from the build environment (no access to the dataset hosts) and are measured by the code when you load the real files.

## Selected datasets

| Criterion | Dataset A: TUANDROMD (static) | Dataset B: CIC-AndMal2017 (network) |
|---|---|---|
| Authentic source | UCI Machine Learning Repository, dataset 855 (https://archive.ics.uci.edu/dataset/855/tuandromd+(tezpur+university+android+malware+dataset)); a preprocessed version is UCI dataset 813 | Canadian Institute for Cybersecurity, Univ. of New Brunswick (https://www.unb.ca/cic/datasets/andmal2017.html) |
| Original research | Borah, Bhattacharyya, Kalita, IEEE CICT 2020, DOI 10.1109/CICT51604.2020.9312053 (listed as the introductory paper on UCI) | Lashkari, Kadir, Taheri, Ghorbani, "Toward Developing a Systematic Approach to Generate Benchmark Android Malware Datasets and Classification", ICCST 2018 (IEEE 8585560) |
| Android relevance | Android apps (malware vs goodware) | Apps run on real smartphones; traffic captured per app |
| Evidence type | Static: 214 permission + 27 API features (UCI variable notes) | Network: CICFlowMeter-V3 flow statistics (UNB states 80+ features) |
| Number of records | 4,465 instances (UCI; one UCI page shows 4,464), 241 features + label | 10,854 apps collected (4,354 malware, 6,500 benign) per UNB; flow count = **to confirm at run time** (printed by the builder) |
| Target labels | Label: malware / goodware | Benign vs adware / ransomware / scareware / SMS malware, collapsed to binary |
| Class distribution | **to confirm at run time** (shown in the app and EDA) | **to confirm at run time** |
| Download accessibility | Direct CSV on UCI, no login | UNB download page (may ask for a short form); large files |
| Licence | CC BY 4.0 (UCI page) | Free for research with citation; confirm exact wording on the UNB page |
| Identifiers for leakage prevention | None provided, so near-duplicates cannot be grouped (documented limitation) | Capture file per flow, used as GROUP id for group-aware splitting |
| Overall suitability | Good: real labelled data, simple binary task, documented | Good: real device captures, labelled, supports group-aware evaluation |

## Rejected / not used

* **Kaggle competition "Android malware detection"** (https://www.kaggle.com/competitions/android-malware-detection/data): the page
  describes the task as detecting malicious apps from traffic behaviour, but its file list, columns and label availability could not be
  verified, and competitions typically hide the test labels. Provenance is not traceable to an original publication, so it was not used.
* **Kaggle/Mendeley copies of CIC-AndMal2017**: re-packaged CSVs derived from the original; the original UNB source is used instead.
* **TUANDROMD-X (2026)**: multiclass entropy/image features, data available on request; different task.

## Known data-quality concerns to check when you load the files

1. TUANDROMD: UCI reports 4,464 vs 4,465 rows between pages, so a row with a missing label may exist (the loader drops and counts it).
2. TUANDROMD: no app ids, so duplicate or near-duplicate apps may sit in both splits. Exact duplicates are removed first; the rest is a stated limitation.
3. CIC-AndMal2017 flows: `Infinity`/NaN values in rate columns, constant columns, very uneven flows per capture, and identifiers (IPs, Flow ID, timestamps) that would leak capture identity: handled by the loader.
4. CIC-AndMal2017: binary label is derived from the capture folder (benign vs malware category); the builder prints how each file was labelled.
5. Both datasets are from a fixed time window and may not represent current malware.
