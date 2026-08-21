streamlit run app.py

SI-PLATFORM

Kubernetes Automation & Validation Suite

SI-PLATFORM is a Streamlit-based System Integration platform for
Kubernetes validation, comparison, diagnostics, backup operations,
connectivity checks, and cluster reporting.

The project is maintained in the following GitHub repository:

GitHub Repository: https://github.com/Deepakram0929/SI-Platform

Features

Validation & Comparison

Environment Comparator

Compare Kubernetes resources between two environments and identify
configuration differences.

Capabilities include: - Source and destination cluster comparison -
ConfigMap comparison - Secret comparison - DIFF and MISSING detection -
Selective configuration synchronization - Destination update
confirmation

Workload Comparator

Compare Kubernetes workloads across environments.

Supported workload types include: - Deployments - StatefulSets -
DaemonSets - Jobs - CronJobs

Image Comparator

Compare container images used by Kubernetes workloads across
environments.

YAML Comparator

Compare Kubernetes YAML files or exported manifests.

Monitoring & Diagnostics

Ingress Connectivity

Validate ingress endpoints, connectivity, and routing across Kubernetes
environments.

Container Status

Check Kubernetes container/workload status and identify operational
issues.

VM Connectivity

Validate connectivity to required virtual machines and infrastructure
endpoints.

Docker Image Search / Load

Search and work with Docker images required for Kubernetes operations.

Backup & Operations

Namespace Backup

Create and manage namespace-level Kubernetes backups before making
configuration or deployment changes.

DB String

Validate and manage database connection strings and connectivity
configuration.

Reports

Cluster Comparison Report

Generate detailed comparison reports for Kubernetes cluster resources
and configuration.

Reports can be exported to Excel for further analysis.

The report generation uses openpyxl.

Project Structure

The repository currently contains the main application and operational
modules, including:

SI-Platform/
│
├── app.py
├── home.py
├── cluster_comparison_report.py
├── container_status.py
├── db_string.py
├── docker_image_load.py
├── environment_comparator.py
├── image_comparator.py
├── ingress.py
├── namespace_backup.py
├── vm_connectivity.py
├── workload_comparator.py
├── yaml_comparator.py
│
├── kubernetes_automation.png
├── requirements.txt
├── read.me
└── README.md

The exact project structure can change as new modules are added.

System Requirements

Before setting up SI-PLATFORM, install:

Python

Git

kubectl if Kubernetes cluster operations are required

Access to the required Kubernetes clusters

Valid Kubernetes kubeconfig files where applicable

Verify Python:

python --version

Verify Git:

git --version

Verify kubectl:

kubectl version --client

The repository does not currently define a fixed Python version. Use a
Python version supported by the installed project dependencies.

Setup Guide

Step 1 - Clone the Repository

Open PowerShell or a terminal and run:

git clone https://github.com/Deepakram0929/SI-Platform.git

Move into the project directory:

cd SI-Platform

You can also open the project directly in VS Code:

code .

Step 2 - Create a Python Virtual Environment

Create a virtual environment:

python -m venv .venv

Activate it on Windows PowerShell:

.\.venv\Scripts\Activate.ps1

If the activation script is blocked by the PowerShell execution policy,
use:

.\.venv\Scripts\activate

After activation, the terminal should show something similar to:

(.venv) PS C:\...\SI-Platform>

Step 3 - Upgrade pip

Run:

python -m pip install --upgrade pip

Step 4 - Install Project Dependencies

The repository's requirements.txt currently contains:

streamlit
kubernetes
pyyaml
pandas
openpyxl
paramiko

Install all dependencies with:

pip install -r requirements.txt

Or:

python -m pip install -r requirements.txt

Verify Installation

Check Streamlit:

streamlit --version

Check Python packages:

pip list

You should see the project dependencies installed, including:

streamlit
kubernetes
PyYAML
pandas
openpyxl
paramiko

Run SI-PLATFORM

From the project directory:

streamlit run app.py

The application will normally start on:

http://localhost:8501

You can open the application in your browser:

http://localhost:8501

The repository's current quick-start instruction is also:

streamlit run app.py

Complete Windows Setup

For a new Windows machine, the complete setup can be performed as
follows:

git clone https://github.com/Deepakram0929/SI-Platform.git

cd SI-Platform

python -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip

pip install -r requirements.txt

streamlit run app.py

Then open:

http://localhost:8501

Updating the Project

To get the latest changes from GitHub:

git pull origin main

If the virtual environment is already created, activate it:

.\.venv\Scripts\Activate.ps1

Update dependencies if requirements.txt has changed:

pip install -r requirements.txt

Then start the application:

streamlit run app.py

Running After Restarting the Machine

After restarting Windows:

cd "C:\Path\To\SI-Platform"

.\.venv\Scripts\Activate.ps1

streamlit run app.py

Replace the path with the actual location of the cloned repository.

Kubernetes Access Setup

Modules that interact with Kubernetes require access to the appropriate
cluster.

Verify that kubectl is installed:

kubectl version --client

Check the current Kubernetes context:

kubectl config current-context

List available contexts:

kubectl config get-contexts

Test cluster connectivity:

kubectl get nodes

If the application requires a specific kubeconfig, ensure the
appropriate kubeconfig is available to the environment where the
application is running.

Environment Comparator Workflow

A typical environment comparison workflow is:

Source Environment
       │
       ▼
Connect / Upload Kubeconfig
       │
       ▼
Read Kubernetes Resources
       │
       ▼
Destination Environment
       │
       ▼
Compare Resources
       │
       ▼
DIFF / MISSING Detection
       │
       ▼
Select Required Changes
       │
       ▼
Review Selected Changes
       │
       ▼
Confirm
       │
       ▼
Update Destination

The platform is designed to allow selective updates instead of
automatically applying every detected difference.

DIFF and MISSING

DIFF

DIFF means the key exists in both environments but the values are
different.

Example:

Source:
HOST_IDENTIFIER=dclmprod.stc.com.kw

Destination:
HOST_IDENTIFIER=dclmprod-skb.stc.com.kw

MISSING

MISSING means the key exists in the source but is not present in the
destination.

Operators can select only the required keys before applying changes.

Selective Configuration Updates

Recommended workflow:

Compare source and destination.

Review all DIFF and MISSING values.

Select the required configuration keys.

Review the selected changes.

Confirm the update.

Apply the changes to the destination.

Validate the destination workload.

This helps prevent unwanted configuration changes.

Excel Report Error Handling

The Cluster Comparison Report uses openpyxl to generate Excel files.

Kubernetes ConfigMaps and Secrets can sometimes contain unsupported
control characters. When such data is passed directly to an Excel
worksheet, an error similar to this can occur:

IllegalCharacterError:
cannot be used in worksheets

The report-generation code should sanitize unsupported characters before
writing values with:

ws.append(...)

This is especially important when exporting ConfigMap or Secret values.

Development Workflow

Start the application

streamlit run app.py

Stop the application

Press:

Ctrl + C

Restart after code changes

streamlit run app.py

Then refresh the browser.

For a hard browser refresh:

Ctrl + F5

Troubleshooting

streamlit is not recognized

Use:

python -m streamlit run app.py

If Streamlit is not installed:

pip install streamlit

ModuleNotFoundError

Install all project dependencies:

pip install -r requirements.txt

For example:

pip install kubernetes pyyaml pandas openpyxl paramiko

Application changes are not visible

Stop Streamlit:

Ctrl + C

Start it again:

streamlit run app.py

Then perform:

Ctrl + F5

in the browser.

Virtual environment is not active

Run:

.\.venv\Scripts\Activate.ps1

Verify:

python --version

and:

pip --version

Both should point to the virtual environment.

PowerShell blocks virtual environment activation

If PowerShell reports an execution-policy error, you can activate the
environment using:

.\.venv\Scripts\activate

Alternatively, use Command Prompt:

.venv\Scripts\activate.bat

Kubernetes connection fails

Check:

kubectl config current-context

Then:

kubectl get nodes

If the command fails, resolve kubeconfig, credentials, network, or
cluster-access issues before using the Kubernetes modules.

Security

The platform may process sensitive infrastructure information,
including:

Kubernetes kubeconfig information

ConfigMap values

Secret values

Database connection strings

Internal service URLs

VM connectivity information

Cluster configuration

Do not commit sensitive credentials to GitHub.

Do not store the following in the repository:

Passwords
API keys
Tokens
Private certificates
Production kubeconfigs
Database credentials

Use approved secure configuration and secret-management mechanisms.

Recommended Production Practices

Before applying changes to a production environment:

Verify the source cluster.

Verify the destination cluster.

Confirm the namespace.

Review DIFF values.

Review MISSING values.

Select only the required changes.

Take a backup where applicable.

Review the final destination update.

Apply the change.

Validate the workload and connectivity afterward.

Git Workflow

Check the current status:

git status

Pull the latest changes:

git pull origin main

Create a feature branch:

git checkout -b feature/<feature-name>

Review changes:

git diff

Stage changes:

git add .

Commit:

git commit -m "Update SI-PLATFORM"

Push the branch:

git push origin feature/<feature-name>

Quick Reference

Task                                Command

Clone project                       git clone https://github.com/Deepakram0929/SI-Platform.git

Enter project                       cd SI-Platform

Create venv                         python -m venv .venv

Activate venv                       .\.venv\Scripts\Activate.ps1

Upgrade pip                         python -m pip install --upgrade pip

Install dependencies                pip install -r requirements.txt

Run application                     streamlit run app.py

Check kubectl                       kubectl version --client

Check cluster                       kubectl get nodes

Check Git changes                   git status

Update project                      git pull origin main

Architecture Overview

                    ┌───────────────────────┐
                    │      SI-PLATFORM      │
                    │   Streamlit App       │
                    └───────────┬───────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
   Validation &             Monitoring &          Backup &
    Comparison              Diagnostics           Operations
          │                     │                     │
          ▼                     ▼                     ▼
 Environment              Ingress / VM /       Namespace Backup /
 Workload / Image /        Container / Docker   DB String
 YAML Comparison
          │
          ▼
   Cluster Comparison
        Reports
          │
          ▼
       Excel / XLSX

Project Objective

SI-PLATFORM provides a centralized operational interface for System
Integration teams to:

Compare

Validate

Diagnose

Backup

Connect

Operate

Synchronize

Report

across Kubernetes environments.

The goal is to reduce manual operational effort, improve configuration
validation, and provide safer, repeatable Kubernetes
environment-management workflows.

Repository

Official GitHub repository:

https://github.com/Deepakram0929/SI-Platform

To get the latest version:

git clone https://github.com/Deepakram0929/SI-Platform.git

Then follow the setup steps in this README.