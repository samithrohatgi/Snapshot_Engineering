# Raspberry Pi S3 Photo Uploader

A Python-based photo uploading system designed for a Raspberry Pi Zero W. The application monitors network connectivity and automatically uploads locally stored photos to Amazon S3 when an internet connection is available.

The project is being developed with mock components so that functionality can be implemented and tested without access to the physical Raspberry Pi or AWS infrastructure.

## Project Overview

This application is part of a larger Raspberry Pi photo booth system. A separate component handles capturing photos through a camera module when a physical button is pressed.

This project is responsible for managing those photos after capture, ensuring they are reliably uploaded to Amazon S3.

### Intended Workflow

1. The Raspberry Pi boots and automatically starts the uploader.
2. A separate camera application captures photos and saves them locally.
3. The uploader periodically checks for internet connectivity through `UCLA_WEB`.
4. When connectivity is available, the uploader identifies pending photos.
5. Pending photos are uploaded to an Amazon S3 bucket over HTTPS.
6. Each local photo is deleted only after its upload is confirmed successful.
7. Failed uploads remain stored locally and are retried during subsequent upload cycles.

## Architecture

The application is divided into four main components:

| Component | Responsibility |
|---|---|
| `PhotoStore` | Discover, manage, and delete locally stored photos |
| `NetworkChecker` | Monitor network connectivity and internet availability |
| `S3Uploader` | Upload photos to Amazon S3 over HTTPS |
| `SyncManager` | Coordinate connectivity checks, batch uploads, retries, and cleanup |

Each component will have mock implementations for local development and testing.

The project is designed to separate hardware-specific functionality from application logic, allowing mock adapters to be replaced with real implementations during deployment.

## Tech Stack

- **Language:** Python 3
- **Hardware:** Raspberry Pi Zero W
- **Network:** UCLA_WEB Wi-Fi
- **Cloud Storage:** Amazon S3
- **Communication:** HTTPS
- **Testing:** pytest
- **Dependency Management:** pip and Python virtual environments

## Repository Structure

```text
pi-s3-uploader/
├── src/                   # Application source code
├── tests/                 # Unit tests and mocks
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development/testing dependencies
├── .gitignore
└── README.md
```

## Getting Started

### Prerequisites

- Python 3
- pip
- Git

### 1. Clone the Repository

```bash
git clone <repository-url>
cd pi-s3-uploader
```

### 2. Create a Virtual Environment

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

### 4. Run Tests

Once tests have been implemented:

```bash
python -m pytest
```

## Development Strategy

Development will proceed in stages:

### Phase 1: Local Photo Management
- Identify pending photos in a specified directory.
- Delete photos after confirmed successful uploads.
- Prevent accidental deletion of photos that have not been uploaded.

### Phase 2: Mock Network Connectivity
- Implement a network adapter that reports connectivity status.
- Simulate Wi-Fi disconnections and reconnections.
- Test periodic connectivity checks.

### Phase 3: Mock S3 Uploading
- Simulate HTTP uploads to an S3 bucket.
- Handle successful and failed uploads.
- Test batch uploading and retry behavior.

### Phase 4: Integration
- Combine the components into a continuous synchronization loop.
- Ensure failed uploads remain queued.
- Test recovery after application restarts and interrupted connections.

### Phase 5: Raspberry Pi and AWS Deployment
- Replace mock components with production implementations.
- Integrate with UCLA_WEB connectivity.
- Configure secure S3 uploads.
- Configure automatic application startup on Raspberry Pi boot.
- Validate the complete system using actual photographs.

## Reliability and Security

The uploader is intended to follow these principles:

- **Offline operation:** Photos remain stored locally when internet access is unavailable.
- **Upload confirmation:** Local photos are deleted only after successful upload confirmation.
- **Failure recovery:** Failed uploads are retained for subsequent attempts.
- **Batch processing:** Multiple pending photos are uploaded when connectivity becomes available.
- **Secure transmission:** AWS uploads use HTTPS.
- **Credential protection:** AWS credentials and secrets must never be committed to Git.
- **Modularity:** Hardware and cloud dependencies are isolated behind replaceable interfaces.

## Project Status

**In development — initial environment setup and architecture design.**

The current focus