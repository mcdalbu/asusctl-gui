# ASUS Control

Interface nativa **GTK4/Libadwaita**, em português brasileiro, para controlar
laptops ASUS no Linux. Adaptada ao **Vivobook S 14 S5406SA**, com detecção dos
recursos disponíveis. Segue o tema claro/escuro do sistema e adapta a navegação
para janelas estreitas.

## Controles

- **Energia:** Silencioso, Equilibrado e Desempenho, conforme a lista do asusd;
  configuração e ativação/desativação dos perfis automáticos na tomada e na
  bateria. Selecione o perfil e o estado da alternância, depois clique em Salvar.
- **Bateria:** leitura do estado e do limite de carga; escolha de 20–100%,
  atalhos para 60/80/100% e carga completa temporária gerenciada pelo asusd.
  Alterações são enviadas apenas ao clicar em Aplicar/Ativar.
- **Teclado:** intensidade da iluminação via D-Bus/UPower, independente de Aura.
  O número de níveis vem do hardware; no S5406SA consultado são quatro (0–3).
- **Sistema:** modelo, kernel, versão do asusctl, recursos e diagnóstico.

A descoberta é somente leitura e ocorre fora da thread gráfica. Recursos sem
suporte não ganham controles. Falhas de comunicação e aplicação aparecem na
página; a aplicação não inventa valores quando uma leitura falha. Use Atualizar
na página para consultar mudanças feitas por atalhos ou outros aplicativos; o
botão do cabeçalho refaz a detecção dos recursos.

Na instalação consultada (Fedora 44, asusctl 6.3.8), o asusd informa
`ThrottlePolicy` e `ChargeControlEndThreshold`. Não oferece interfaces Aura,
FanCurves ou AsusArmoury. A interface Backlight do daemon, por si só, não
comprova a presença de um ScreenPad. Por isso a GUI não oferece controles de
ScreenPad, RGB, curvas de ventoinha ou modos de carregamento Armoury.
Isso descreve os serviços desta instalação, não uma garantia para toda a
família S5406. A GUI não adiciona suporte ausente no kernel/firmware/daemon.

## Executar

Requisitos: Python 3.11+, PyGObject, GTK 4.10+, Libadwaita 1.4+, asusctl com os
subcomandos `profile list/get/set` e `battery info/limit/oneshot`, e UPower.

No Fedora, com um repositório que forneça asusctl já configurado:

```bash
sudo dnf install asusctl python3-gobject gtk4 libadwaita upower
systemctl status asusd.service upower.service
```

Execute a partir da pasta do projeto com o Python da distribuição:

```bash
/usr/bin/python3 -m asusctl_gui.main
```

Não execute a GUI como root. As alterações passam pelos serviços do sistema.
Se o asusd estiver indisponível, a página Sistema mostra o erro e o teclado
continua disponível quando o UPower responde. Depois de corrigir o serviço,
clique em Atualizar no cabeçalho para detectar os controles novamente.

## Instalar pelo RPM (Fedora 44)

Baixe `asusctl-gui-1.1.1-1.fc44.noarch.rpm` na
[release v1.1.1](https://github.com/mca-afk/asusctl-gui/releases/tag/v1.1.1).
O repositório é privado: é preciso estar autenticado com acesso a ele para baixar.
Na pasta onde salvou o arquivo, execute:

```bash
sudo dnf install ./asusctl-gui-1.1.1-1.fc44.noarch.rpm
```

O DNF baixa e instala automaticamente as dependências e suas dependências
transitivas pelos repositórios habilitados:

| Dependência | Versão mínima | Função |
|---|---|---|
| Python 3 | 3.11 | Execução da aplicação; o RPM também exige o ABI Python da distribuição de build |
| python3-gobject | 3.42 | Acesso às bibliotecas GTK e D-Bus |
| gtk4 | 4.10 | Interface gráfica |
| libadwaita | 1.4 | Componentes nativos do GNOME |
| asusctl | 6.3.8 | Cliente e daemon de controle do laptop |
| upower | Fornecida pela distribuição | Iluminação do teclado |

O pacote é uma instalação online: contém a aplicação e os requisitos RPM;
as bibliotecas são gerenciadas pelo sistema. Use `dnf install`, pois `rpm -ivh`
sozinho não baixa dependências.

O `asusctl` precisa estar disponível em um repositório habilitado. No Fedora 44
validado, ele é fornecido pelo COPR `lukenukem/asus-linux`. Se esse repositório
ainda não estiver configurado e o DNF não encontrar `asusctl >= 6.3.8`, habilite-o
antes da instalação:

```bash
sudo dnf copr enable lukenukem/asus-linux
sudo dnf install ./asusctl-gui-1.1.1-1.fc44.noarch.rpm
```

Após instalar, abra **ASUS Control** no menu de aplicativos ou execute:

```bash
asusctl-gui
```

Se os controles do laptop não aparecerem, consulte os serviços:

```bash
systemctl status asusd.service upower.service
```

A release inclui `SHA256SUMS` e um RPM de fontes. Para verificar os arquivos
que baixou, coloque-os junto ao arquivo de checksums e execute:

```bash
sha256sum --check --ignore-missing SHA256SUMS
```

### Construir o RPM

```bash
sudo dnf install rpm-build python3-devel
./build_rpm.sh
```

O build gera os RPMs em `build/rpmbuild/` e exporta os arquivos desta versão,
com checksums, para `build/releases/v1.1.1/`. Nenhum pacote é instalado durante
o build. O RPM publicado é para Fedora 44; para outra distribuição/versão,
reconstrua nele para obter os caminhos e o ABI Python correspondentes.

## Verificação

```bash
/usr/bin/python3 -m unittest discover -s tests -v
appstreamcli validate --no-net data/org.asuslinux.AsusctlGui.metainfo.xml
```

Para incluir os testes GTK em uma sessão gráfica:

```bash
ASUSCTL_GUI_TEST_DISPLAY=1 /usr/bin/python3 -m unittest discover -s tests -v
```

Os testes usam respostas simuladas para cobrir detecção, erros e validação
sem alterar o hardware. A validação na sessão gráfica pode ler os recursos
reais; testes automatizados não precisam mudar as configurações do laptop.

O teste integrado com hardware real é opt-in e altera temporariamente as
configurações, salvando e restaurando os valores originais em `finally`:

```bash
/usr/bin/python3 tests/live_hardware.py --allow-hardware-changes
```

O resultado fica em `build/validation-live.json`. Não é executado pelo build
RPM nem pela suíte padrão. Não cobre desconexão física da tomada nem um ciclo
completo de carga. Veja `docs/VALIDACAO.md` para os resultados obtidos.

## Ícone

O ícone vetorial em `data/asusctl-gui.svg` combina a marca ASUS branca,
um fundo azul arredondado e controles de ajuste. A geometria da marca vem do
[SVG publicado pela ASUS](https://www.asus.com/media/img/2017/images/n-logo-asus.svg).

## Referências

- [asusctl](https://github.com/OpenGamingCollective/asusctl)
- [UPower KbdBacklight](https://upower.freedesktop.org/docs/KbdBacklight.html)

Licença: GPL-3.0-or-later; consulte `LICENSE`.
