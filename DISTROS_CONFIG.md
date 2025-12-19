# Distribution Configuration

Diese Datei (`distros.yaml`) definiert alle unterstützten Linux-Distributionen und deren Architekturen für den DEB-Paket-Build.

## Struktur

```yaml
distributions:
  - distro: debian              # Distributionstyp (debian/ubuntu)
    version: "12"               # Versionsnummer
    codename: bookworm          # Codename der Distribution
    display_name: "Debian 12 (Bookworm)"  # Anzeigename (optional)
    architectures: [amd64, arm64, armhf, riscv64]  # Unterstützte Architekturen
    eol: "2026-06"             # End-of-Life Datum (YYYY-MM, optional)
```

## Felder

### Pflichtfelder

- **distro**: Distributionstyp (`debian` oder `ubuntu`)
- **version**: Offizielle Versionsnummer (z.B. `"12"`, `"22.04"`)
- **codename**: Offizieller Codename (z.B. `bookworm`, `jammy`)
- **architectures**: Array der unterstützten CPU-Architekturen
  - Verfügbar: `amd64`, `arm64`, `armhf`, `riscv64`, `i386`
  - Jede Distribution kann unterschiedliche Architekturen haben
  - Hinweis: riscv64 wird nur von neueren Distributionen unterstützt (Debian 13+, Ubuntu 24.04+)

### Optionale Felder

- **display_name**: Lesbarer Name für Dokumentation
- **eol**: End-of-Life Datum im Format `YYYY-MM`
  - Hilft beim Tracking des Support-Lebenszyklus

## Verwendung

Diese Konfiguration wird automatisch von folgenden Komponenten verwendet:

1. **Build Workflow** ([.github/workflows/build-deb.yml](../.github/workflows/build-deb.yml))
   - Generiert Build-Matrix für alle Distribution/Architektur-Kombinationen
   - Erstellt DEB-Pakete für jede Kombination

2. **Matrix-Generator** ([.github/scripts/generate-matrix.py](../.github/scripts/generate-matrix.py))
   - Liest die YAML-Konfiguration
   - Generiert JSON-Matrix für GitHub Actions

## Neue Distribution hinzufügen

Um Unterstützung für eine neue Distribution hinzuzufügen:

1. Füge einen Eintrag zum `distributions`-Array in `distros.yaml` hinzu
2. Committe und pushe die Änderungen
3. Der Workflow wird automatisch:
   - Die neue Distribution zur Build-Matrix hinzufügen
   - Pakete für alle angegebenen Architekturen erstellen

Beispiel:

```yaml
distributions:
  - distro: ubuntu
    version: "26.04"
    codename: plucky
    display_name: "Ubuntu 26.04 LTS"
    architectures: [amd64, arm64]
    eol: "2031-04"
```

## Architektur-Support

Jede Distribution kann ihre eigenen unterstützten Architekturen definieren. Dies ermöglicht Flexibilität für:

- Ältere Distributionen, die ARM64 nicht unterstützen
- Spezialisierte Distributionen mit besonderen Architektur-Anforderungen
- Schrittweise Migration der Architektur-Unterstützung

Beispiel mit unterschiedlichen Architekturen:

```yaml
distributions:
  - distro: debian
    codename: bullseye
    version: "11"
    architectures: [amd64, armhf]  # Keine arm64/riscv64 Unterstützung

  - distro: debian
    codename: bookworm
    version: "12"
    architectures: [amd64, arm64, armhf, riscv64]  # Volle Unterstützung
```

## Validierung

Die Konfiguration wird automatisch während der Workflow-Ausführung validiert. Stelle sicher:

- Alle Pflichtfelder sind vorhanden
- Architekturnamen sind gültige Debian-Architekturnamen
- Codenamen sind eindeutig
- YAML-Syntax ist korrekt

Lokal testen:

```bash
# YAML-Syntax validieren
python3 -c "import yaml; yaml.safe_load(open('distros.yaml'))"

# Matrix-Generierung testen
python3 .github/scripts/generate-matrix.py
```

## Aktuell unterstützte Distributionen

Die derzeit konfigurierten Distributionen sind:

- **Debian 12 (Bookworm)**: amd64, arm64, armhf (3 Pakete)
- **Debian 13 (Trixie)**: amd64, arm64, armhf, riscv64 (4 Pakete)
- **Ubuntu 22.04 LTS (Jammy)**: amd64, arm64, armhf (3 Pakete)
- **Ubuntu 24.04 LTS (Noble)**: amd64, arm64, armhf, riscv64 (4 Pakete)

Insgesamt: **14 Pakete** pro Build (6 + 8)

**Hinweis:** riscv64 wird nur von neueren Distributionen unterstützt (Debian 13/Trixie und Ubuntu 24.04/Noble),
da erst ab diesen Versionen offizielle Docker-Images mit riscv64-Varianten verfügbar sind.
