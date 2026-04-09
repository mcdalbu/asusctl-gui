# asusctl-gui

Uma interface gráfica GTK4/Adwaita para o daemon `asusd`/`asusctl` em laptops ASUS rodando Linux (Fedora 43+).

## Funcionalidades

| Recurso | Descrição |
|---------|-----------|
| **Perfis de energia** | Alterna entre Quiet, Balanced e Performance |
| **Limite de bateria** | Slider 20–100 % com aplicação imediata |
| **Modo de carregamento** | Full Capacity / Balanced / Maximum Lifespan via armoury |
| **Backlight** | Brilho e gamma do screenpad |
| **Detecção automática** | Recursos não suportados pelo hardware ficam ocultos |

## Pré-requisitos

```bash
sudo dnf install asusctl python3-gobject gtk4 libadwaita
```

O serviço `asusd` deve estar ativo:

```bash
systemctl status asusd
```

## Executar diretamente (sem instalar)

```bash
cd /home/mcda/Antigravity\ Projects/asusctl-gui
python3 -m asusctl_gui.main
```

## Instalar via RPM (recomendado)

### 1. Instalar dependências de build

```bash
sudo dnf install rpmdevtools rpm-build
```

### 2. Construir o RPM

```bash
cd /home/mcda/Antigravity\ Projects/asusctl-gui
chmod +x build_rpm.sh
./build_rpm.sh
```

### 3. Instalar o RPM gerado

```bash
sudo rpm -ivh ~/rpmbuild/RPMS/noarch/asusctl-gui-1.0.0-1.fc43.noarch.rpm
```

Ou usando dnf (resolve dependências automaticamente):

```bash
sudo dnf install ~/rpmbuild/RPMS/noarch/asusctl-gui-1.0.0-1.fc43.noarch.rpm
```

### 4. Lançar

Pesquise por **"ASUS Control"** no GNOME Activities, ou execute:

```bash
asusctl-gui
```

## Desinstalar

```bash
sudo rpm -e asusctl-gui
```

## Estrutura do projeto

```
asusctl-gui/
├── asusctl_gui/
│   ├── backend/
│   │   ├── asusctl.py       # Wrapper CLI → Python
│   │   └── system_info.py   # Detecção de features
│   ├── pages/
│   │   ├── profile_page.py
│   │   ├── battery_page.py
│   │   ├── backlight_page.py
│   │   └── info_page.py
│   ├── window.py
│   ├── main.py
│   └── style.css            # Tema dark ROG
├── data/
│   ├── asusctl-gui.desktop
│   └── asusctl-gui.svg
├── packaging/
│   └── asusctl-gui.spec
└── build_rpm.sh
```

## Licença

GPLv3+
