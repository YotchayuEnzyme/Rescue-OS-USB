\# Rescue-OS-USB 🛠️

> Automated Diagnostic \& Recovery Engine for PC Storage \& Bootloader Issues



An open-source, minimal live-boot environment designed to automatically inspect hardware health, diagnose corrupted bootloaders, and perform non-destructive recovery actions without booting the host operating system.



\---



\## 📌 Background \& Motivation

When an operating system fails to boot (e.g., stuck in Windows Automatic Repair loops or corrupted EFI partitions), typical recovery methods require manual terminal commands or heavy, complex tools. 



\*\*Rescue-OS-USB\*\* provides a fast, lightweight, and automated triage engine running directly from RAM to diagnose and repair storage issues safely.



\---



\## ✨ Key Features

\- \*\*Read-Only Inspection First:\*\* Safely scans partition tables and filesystems without risk of accidental data loss.

\- \*\*Hardware Health Diagnostics:\*\* Verifies NVMe/SATA drive status via S.M.A.R.T. telemetry.

\- \*\*Automated Bootloader Verification:\*\* Scans for `bootmgfw.efi`, BCD configurations, and active boot flags.

\- \*\*Crash \& Power-Failure Resilience:\*\* Designed to run in-memory (Diskless Mode) to prevent corruption if the USB drive is detached during analysis.



\---



\## 🏗️ System Architecture

```text

\[BIOS/UEFI Boot]

&#x20;      │

&#x20;      ▼

\[Minimal Alpine Linux (RAM Disk)]

&#x20;      │

&#x20;      ▼

\[Rescue-OS Core Engine (C++ / Bash)]

&#x20;      │

&#x20;      ├──► Storage Discovery \& Exclusion (Ignores Boot Drive)

&#x20;      ├──► Partition Integrity \& BitLocker Detection

&#x20;      └──► EFI \& System File Triage Report```



\## 🛠️Tech Stack

OS Environment: Alpine Linux (Copy-to-RAM mode)



Core Engine: C++ / POSIX Shell Scripting



Target Systems: Windows (NTFS / FAT32 EFI), Linux (ext4 / GRUB)



Utilities: lsblk, smartctl, efibootmgr, partclone



\## 🗺️ Roadmap

\[x] Initial repository setup \& architecture design



\[ ] Core storage discovery \& safe-read implementation



\[ ] Automated EFI partition health analyzer



\[ ] Minimal TUI / Human-readable diagnostic output



\[ ] ISO packaging for Ventoy \& live USB deployment



Note: This is my first GitHub project. Initial documentation scaffolding and structure were assisted by AI to match open-source repository standards^^.

