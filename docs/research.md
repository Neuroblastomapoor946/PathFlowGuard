# Research Basis

## Selected 2026 Pain Point

The chosen problem is digital pathology scan quality control and secure edge-to-cloud ingestion.

Why this problem is worth building around:

1. Pathology services remain under workforce pressure while workload and complexity continue to rise.
2. Digital pathology still consumes substantial manual effort in scan prep, QC, rescans, and image management.
3. Whole-slide image artifacts can silently degrade or break downstream AI and analytics.
4. Connected medical software now faces stronger explicit cybersecurity expectations from FDA.

## Evidence

### 1. Workforce pressure is real

In a 2024 review of the global pathology workforce, Walsh and Orsi describe significant service pressure from declining or aging workforces, greater workload volume, and greater case complexity.

Link:
https://pmc.ncbi.nlm.nih.gov/articles/PMC11662708/

Relevant points:

- Abstract: the workforce faces significant pressures from numbers, age profile, and complexity.
- The review cites increasing workload and complexity per case, including rising slide counts and additional testing burden.

### 2. Digital pathology operations are still manually expensive

Memorial Sloan Kettering published an operations and cost study showing that pre-scan and post-scan QC account for most scan-team effort. The paper also notes that insufficient manual inspection and cleaning materially increases rescan likelihood, and that IT/storage infrastructure is one of the largest cost categories.

Link:
https://pmc.ncbi.nlm.nih.gov/articles/PMC10550754/

Relevant points:

- Pre-scan and post-scan QC are major time allocations for scan teams.
- Consult slides that are not manually inspected and prepped showed a 50% higher likelihood of requiring rescan.
- A single one-z-plane digital pathology image can be around 2 GB.

### 3. Artifact QC is a bottleneck for downstream AI

The 2024 Nature Communications GrandQC paper explicitly frames QC as a major bottleneck in digital pathology and shows that artifacts can lead to clinically important false positive and false negative misclassifications in downstream AI.

Link:
https://www.nature.com/articles/s41467-024-54769-y

Relevant points:

- QC is called a significant bottleneck for implementation.
- Artifacts are present in virtually all histological slides.
- Artifacts can cause critical misclassifications in downstream image-analysis pipelines.

### 4. Cybersecurity requirements continue to tighten

FDA’s cybersecurity page states that on June 27, 2025 the agency issued final guidance for "Cybersecurity in Medical Devices: Quality System Considerations and Content of Premarket Submissions" and ties cybersecurity risk to device safety and effectiveness.

Link:
https://www.fda.gov/medical-devices/digital-health-center-excellence/cybersecurity

Relevant points:

- Connected medical products can create cybersecurity risks that affect safety and effectiveness.
- FDA expects cybersecurity to be handled as part of quality-system and lifecycle work, not as an afterthought.

## Why This Specific Project

This project sits at a useful intersection:

- Python: orchestration, policy engine, cloud workflow integration
- C++: high-throughput image metric computation on large slide tiles
- Rust: secure manifesting, integrity, and edge-side hardening
- Cloud: queueing, storage, audit, reliability, and remote review workflows

It also maps well to the requested experience profile:

- CI/CD and automated testing
- system performance and reliability
- cybersecurity across edge and cloud
- IEC 62304 / ISO 13485 / ISO 14971 style process discipline
- diagnostics / digital pathology / medical imaging domain relevance

