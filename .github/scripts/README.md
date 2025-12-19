# Build Scripts

Dieses Verzeichnis enthält alle Skripte, die für den Debian-Paket-Build-Prozess verwendet werden.

## Skripte

### generate-matrix.py
Generiert die GitHub Actions Build-Matrix aus `distros.yaml`.

**Verwendung:**
```bash
python3 generate-matrix.py
```

**Ausgabe:** JSON-Matrix im Single-Line-Format für GitHub Actions

---

### update-version.sh
Aktualisiert die Versionsnummern in `pyproject.toml` und `debian/changelog`.

**Verwendung:**
```bash
./update-version.sh VERSION CODENAME
```

**Parameter:**
- `VERSION`: Die neue Versionsnummer (z.B. "1.2.3")
- `CODENAME`: Der Codename der Distribution (z.B. "bookworm", "jammy")

**Beispiel:**
```bash
./update-version.sh 1.2.3 bookworm
```

---

### build-deb-docker.sh
Erstellt ein DEB-Paket in einem Docker-Container für eine spezifische Distribution und Architektur.

**Verwendung:**
```bash
./build-deb-docker.sh DISTRO CODENAME ARCH
```

**Parameter:**
- `DISTRO`: Distribution (debian oder ubuntu)
- `CODENAME`: Codename der Version (bookworm, trixie, jammy, noble)
- `ARCH`: Zielarchitektur (amd64, arm64, armhf, riscv64)

**Beispiel:**
```bash
./build-deb-docker.sh debian bookworm amd64
```

**Ausgabe:** DEB-Pakete im Verzeichnis `deb-packages/`

---

### organize-packages.sh
Organisiert die erstellten DEB-Pakete in einer APT-Repository-Struktur.

**Verwendung:**
```bash
./organize-packages.sh [INPUT_DIR] [OUTPUT_DIR]
```

**Parameter:**
- `INPUT_DIR`: Verzeichnis mit den heruntergeladenen Artifacts (Standard: `all-debs`)
- `OUTPUT_DIR`: Zielverzeichnis für das Repository (Standard: `apt-repo`)

**Beispiel:**
```bash
./organize-packages.sh all-debs apt-repo
```

**Struktur:** Erstellt Verzeichnisse wie `apt-repo/debian/bookworm/binary-amd64/`

---

### create-packages-files.sh
Erstellt `Packages` und `Packages.gz` Dateien für das APT-Repository.

**Verwendung:**
```bash
./create-packages-files.sh [REPO_DIR]
```

**Parameter:**
- `REPO_DIR`: Root-Verzeichnis des Repositories (Standard: `apt-repo`)

**Beispiel:**
```bash
./create-packages-files.sh apt-repo
```

**Ausgabe:** `Packages` und `Packages.gz` in jedem binary-* Verzeichnis

---

### create-release-files.sh
Erstellt `Release` Dateien für das APT-Repository.

**Verwendung:**
```bash
./create-release-files.sh [REPO_DIR]
```

**Parameter:**
- `REPO_DIR`: Root-Verzeichnis des Repositories (Standard: `apt-repo`)

**Beispiel:**
```bash
./create-release-files.sh apt-repo
```

**Ausgabe:** `Release` Dateien in jedem Distributions-Verzeichnis

---

### create-repo-readme.sh
Erstellt eine README-Datei für das APT-Repository mit Installationsanweisungen.

**Verwendung:**
```bash
./create-repo-readme.sh VERSION VERSION_TAG [OUTPUT_FILE]
```

**Parameter:**
- `VERSION`: Die Versionsnummer (z.B. "1.2.3")
- `VERSION_TAG`: Der Git-Tag (z.B. "v1.2.3")
- `OUTPUT_FILE`: Ausgabedatei (Standard: `apt-repo/README.md`)

**Beispiel:**
```bash
./create-repo-readme.sh 1.2.3 v1.2.3 apt-repo/README.md
```

---

## Workflow-Integration

Diese Skripte werden im [build-deb.yml](../../workflows/build-deb.yml) Workflow verwendet:

1. **generate-matrix.py** → Generiert die Build-Matrix
2. **update-version.sh** → Aktualisiert Versionen vor dem Build
3. **build-deb-docker.sh** → Erstellt DEB-Pakete
4. **organize-packages.sh** → Organisiert Pakete
5. **create-packages-files.sh** → Erstellt Packages-Dateien
6. **create-release-files.sh** → Erstellt Release-Dateien
7. **create-repo-readme.sh** → Erstellt Repository-README

## Lokales Testen

Alle Skripte können auch lokal ausgeführt werden, um den Build-Prozess zu testen:

```bash
# Build lokal für Debian 12 auf amd64
./build-deb-docker.sh debian bookworm amd64

# Pakete organisieren
./organize-packages.sh deb-output apt-repo

# Repository-Metadaten erstellen
./create-packages-files.sh apt-repo
./create-release-files.sh apt-repo
./create-repo-readme.sh 1.0.0 v1.0.0 apt-repo/README.md
```

## Voraussetzungen

- **Für Python-Skripte**: Python 3.x mit `pyyaml`
- **Für Docker-Builds**: Docker mit QEMU-Support für Cross-Compilation
- **Für Repository-Erstellung**: `dpkg-dev`, `apt-utils`, `gnupg`

## Wartung

Bei Änderungen an der Build-Logik:

1. Aktualisiere das entsprechende Skript
2. Teste lokal mit verschiedenen Distributionen/Architekturen
3. Aktualisiere diese README bei Änderungen an den Schnittstellen
4. Stelle sicher, dass alle Skripte executable sind (`chmod +x *.sh`)
