# Entrada de meta-harness para Windows (compatible con Windows PowerShell 5.1 y PowerShell 7).
# Prepara WSL2 + Ubuntu y relanza dentro de Ubuntu el comando unico de Linux (instalar.sh).
# Uso:
#   irm https://raw.githubusercontent.com/catrroberrtt/meta-harness/main/bootstrap/instalar.ps1 | iex
#   .\instalar.ps1 -Instancia owner/nombre [-Distribucion Ubuntu-24.04] [-Version X.Y.Z] [-Si] [-SoloPlan]
# No pide ni guarda credenciales. Solo ejecuta el instalar.sh publico del repositorio, con la version mostrada.
param(
    [string]$Instancia = '',
    [string]$Distribucion = 'Ubuntu-24.04',
    [string]$Version = '',
    [switch]$Si,
    [switch]$SoloPlan
)

$ErrorActionPreference = 'Continue'

# UNICO lugar de la URL (un fork la cambia aqui o define la variable de entorno MH_RAW_BASE). La guarda de abajo detiene el script si
# la URL conserva el marcador /owner/ de una plantilla sin completar.
$BaseUrl = 'https://raw.githubusercontent.com/catrroberrtt/meta-harness/main/bootstrap'
if ($env:MH_RAW_BASE) { $BaseUrl = $env:MH_RAW_BASE.TrimEnd('/') }

function Escribir([string]$texto) { Write-Host $texto }
function Fallar([string]$texto) { Write-Host ''; Write-Host $texto -ForegroundColor Red; throw 'meta-harness: instalacion detenida. No se cambio nada mas.' }

# La salida de wsl.exe es UTF-16: al leerla llegan caracteres NUL y retornos de carro. Se limpian antes de comparar.
function Limpiar-Wsl($crudo) {
    $texto = ($crudo | Out-String)
    $texto = $texto -replace "`0", ''
    $texto = $texto -replace "`r", ''
    return $texto
}

function Ejecutar-Wsl([string[]]$argumentos) {
    $crudo = & wsl.exe $argumentos 2>&1
    $script:CodigoWsl = $LASTEXITCODE
    return (Limpiar-Wsl $crudo)
}

function Es-Administrador {
    $identidad = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identidad)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Estas confirmaciones NO se saltan con -Si: descargan sistemas completos y pueden obligar a reiniciar el equipo.
function Confirmar-Siempre([string]$pregunta) {
    if ($SoloPlan) { return $false }
    $r = Read-Host ($pregunta + ' [S/N] (-Si no omite esta pregunta)')
    return ($r -match '^[sSyY]')
}

function Confirmar([string]$pregunta) {
    if ($SoloPlan) { return $false }
    if ($Si) { Escribir ($pregunta + ' [S/N]: S (por -Si)'); return $true }
    $r = Read-Host ($pregunta + ' [S/N]')
    return ($r -match '^[sSyY]')
}

# ---------- validacion de lo que se pasa al comando Linux (evita inyectar texto en la linea de comandos) ----------
if ($Instancia -ne '') {
    if ($Instancia -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') { Fallar 'El valor de -Instancia debe tener la forma owner/nombre.' }
}
if ($Version -ne '') {
    if ($Version -notmatch '^[0-9]+\.[0-9]+\.[0-9]+$') { Fallar 'El valor de -Version debe tener la forma X.Y.Z (por ejemplo 1.2.3).' }
}
if ($Distribucion -notmatch '^[A-Za-z0-9_.-]+$') { Fallar 'El valor de -Distribucion solo admite letras, numeros, punto, guion y guion bajo.' }
if ($BaseUrl -match '/owner/') { Fallar 'La URL del repositorio aun tiene el marcador owner. Define la variable de entorno MH_RAW_BASE con la URL real de bootstrap.' }

$UrlLinux = $BaseUrl + '/instalar.sh'
$ComandoLinux = 'curl -fsSL ' + $UrlLinux + ' | sh -s --'
if ($Instancia -ne '') { $ComandoLinux = $ComandoLinux + ' --instancia ' + $Instancia }
if ($Version -ne '') { $ComandoLinux = $ComandoLinux + ' --version ' + $Version }
if ($Si) { $ComandoLinux = $ComandoLinux + ' --si' }
$VersionTexto = 'la ultima publicada'
if ($Version -ne '') { $VersionTexto = $Version }

Escribir ''
Escribir '== meta-harness en Windows =='
Escribir 'Este script prepara WSL2 con Ubuntu y ejecuta dentro de Ubuntu el comando de Linux.'
Escribir 'Los scripts de meta-harness son de Linux: no corren en PowerShell ni en la carpeta de Windows.'

# ---------- 1. deteccion (solo lectura) ----------
$wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
$HayWsl = ($null -ne $wsl)
$EstadoWsl = ''
$Distros = @()
$DistroElegida = ''
if ($HayWsl) {
    $EstadoWsl = Ejecutar-Wsl @('--status')
    $listado = Ejecutar-Wsl @('-l', '-q')
    foreach ($linea in ($listado -split "`n")) {
        $nombre = $linea.Trim()
        if ($nombre -eq '') { continue }
        # docker-desktop y docker-desktop-data son internas de Docker: no sirven para instalar nada.
        if ($nombre -eq 'docker-desktop') { continue }
        if ($nombre -eq 'docker-desktop-data') { continue }
        if ($nombre -match '^[A-Za-z0-9_.-]+$') { $Distros += $nombre }
    }
    if ($Distros -contains $Distribucion) { $DistroElegida = $Distribucion }
    else {
        foreach ($d in $Distros) { if (($DistroElegida -eq '') -and ($d -like 'Ubuntu*')) { $DistroElegida = $d } }
    }
}
$SoloDocker = $false
if ($HayWsl -and ($DistroElegida -eq '')) {
    if ($listado -match 'docker-desktop') { $SoloDocker = $true }
}
$EsAdmin = Es-Administrador

# ---------- 2. plan ----------
Escribir ''
Escribir 'PLAN (todavia no se ha cambiado nada)'
if ($HayWsl) { Escribir '  wsl.exe: encontrado' } else { Escribir '  wsl.exe: NO encontrado (hay que instalar WSL)' }
if ($DistroElegida -ne '') { Escribir ('  Distribucion a usar: ' + $DistroElegida) }
else {
    Escribir ('  Distribucion a usar: ninguna; se instalaria ' + $Distribucion + ' con: wsl --install -d ' + $Distribucion)
    Escribir '    - Necesita PowerShell como administrador y puede pedir reiniciar el equipo.'
}
if ($SoloDocker) { Escribir '  Nota: la unica distribucion es docker-desktop, interna de Docker; no sirve para meta-harness.' }
if ($EsAdmin) { Escribir '  Sesion de administrador: si' } else { Escribir '  Sesion de administrador: no' }
Escribir ('  Dentro de Ubuntu se ejecutara, desde el directorio personal de Linux:')
Escribir ('    ' + $ComandoLinux)
Escribir ('  URL: ' + $UrlLinux)
Escribir ('  Version de meta-harness: ' + $VersionTexto)
if ($Instancia -ne '') { Escribir ('  Instancia: ' + $Instancia) } else { Escribir '  Instancia: (no indicada; el comando de Linux la pedira o instalara solo la herramienta)' }

if ($SoloPlan) {
    Escribir ''
    Escribir 'Modo -SoloPlan: no se ejecuto nada. Quita -SoloPlan para continuar.'
    return
}

# ---------- 3. instalar Ubuntu si hace falta ----------
if ($DistroElegida -eq '') {
    if (-not $EsAdmin) {
        Escribir ''
        Escribir 'Falta Ubuntu y esta sesion no es de administrador. No lo intento.'
        Escribir 'Abre PowerShell como administrador: menu Inicio, escribe PowerShell, clic derecho, Ejecutar como administrador.'
        Escribir 'Luego vuelve a ejecutar el mismo comando que usaste ahora.'
        return
    }
    Escribir ''
    Escribir ('Se va a ejecutar: wsl --install -d ' + $Distribucion)
    Escribir 'Descarga Ubuntu, activa WSL2 si falta y puede pedir reiniciar el equipo.'
    if (-not (Confirmar-Siempre 'Instalar Ubuntu ahora?')) { Escribir 'No se instalo nada.'; return }
    & wsl.exe --install -d $Distribucion
    $codigo = $LASTEXITCODE
    $listado = Ejecutar-Wsl @('-l', '-q')
    foreach ($linea in ($listado -split "`n")) {
        if ($linea.Trim() -eq $Distribucion) { $DistroElegida = $Distribucion }
    }
    if ($DistroElegida -eq '') {
        Escribir ''
        Escribir ('La distribucion todavia no aparece (codigo ' + $codigo + '). Lo normal es que falte reiniciar.')
        Escribir 'Debes reiniciar Windows, abrir Ubuntu desde el menu Inicio para crear tu usuario, y volver a ejecutar el mismo comando.'
        return
    }
}

# ---------- 4. primera ejecucion: usuario y contrasena de Linux (interactivo) ----------
$listo = $false
$intentos = 0
while ((-not $listo) -and ($intentos -lt 3)) {
    $prueba = Ejecutar-Wsl @('-d', $DistroElegida, '--', 'echo', 'ok')
    if (($script:CodigoWsl -eq 0) -and ($prueba.Trim() -eq 'ok')) { $listo = $true }
    else {
        $intentos = $intentos + 1
        Escribir ''
        Escribir ('Ubuntu (' + $DistroElegida + ') aun no esta listo. La primera vez pide crear un usuario y una contrasena de Linux.')
        Escribir 'Esa contrasena es solo de Ubuntu: eligela tu y no la compartas. Se escribe sin mostrar caracteres.'
        Escribir 'Si se abrio una ventana de Ubuntu, completa ahi el usuario y la contrasena y escribe exit.'
        $r = Read-Host 'Pulsa Enter cuando termines (o escribe N para salir)'
        if ($r -match '^[nN]') { Escribir 'Detenido. Vuelve a ejecutar el mismo comando cuando Ubuntu este listo.'; return }
    }
}
if (-not $listo) { Fallar ('No pude comprobar ' + $DistroElegida + ' con: wsl -d ' + $DistroElegida + ' -- echo ok') }
Escribir ('Ubuntu listo: ' + $DistroElegida)

# ---------- 5. comprobaciones dentro de la distro (no cambian nada) ----------
# --cd existe en WSL recientes; si no, se entra al directorio personal dentro de bash (que si es bash).
$ayuda = Ejecutar-Wsl @('--help')
$UsaCd = ($ayuda -match '--cd')
function Correr-Linux([string]$comando, [bool]$capturar) {
    if ($UsaCd) { $a = @('-d', $DistroElegida, '--cd', '~', '--', 'bash', '-lc', $comando) }
    else { $a = @('-d', $DistroElegida, '--', 'bash', '-lc', ('if cd ~; then ' + $comando + '; else exit 1; fi')) }
    if ($capturar) { return (Ejecutar-Wsl $a) }
    & wsl.exe $a
    $script:CodigoWsl = $LASTEXITCODE
    return ''
}

Escribir ''
Escribir 'Comprobando requisitos dentro de Ubuntu (no se cambia nada):'
$faltan = @()
$py = Correr-Linux 'python3 --version' $true
if ($py -match 'Python ([0-9]+)\.([0-9]+)') {
    $mayor = [int]$Matches[1]; $menor = [int]$Matches[2]
    if (($mayor -gt 3) -or (($mayor -eq 3) -and ($menor -ge 12))) { Escribir ('  python3: ' + $py.Trim() + ' (ok)') }
    else { Escribir ('  python3: ' + $py.Trim() + ' (hace falta Python 3.12 o mas)'); $faltan += 'python3 3.12' }
} else { Escribir '  python3: no esta instalado'; $faltan += 'python3 3.12' }
$gt = Correr-Linux 'git --version' $true
if ($gt -match 'git version') { Escribir ('  git: ' + $gt.Trim() + ' (ok)') } else { Escribir '  git: no esta instalado'; $faltan += 'git' }
$cu = Correr-Linux 'curl --version' $true
if ($cu -match 'curl [0-9]') { Escribir '  curl: ok' } else { Escribir '  curl: no esta instalado'; $faltan += 'curl' }
if ($faltan.Count -gt 0) {
    Escribir ('  Faltan: ' + ($faltan -join ', ') + '.')
    Escribir '  No los instalo desde aqui: el comando de Linux los instala con una confirmacion de administrador (sudo) dentro de Ubuntu.'
}

# ---------- 6. lanzar el comando de Linux ----------
Escribir ''
Escribir 'Se va a ejecutar dentro de Ubuntu, desde el directorio personal de Linux:'
Escribir ('  ' + $ComandoLinux)
Escribir ('  URL: ' + $UrlLinux + '   Version: ' + $VersionTexto)
Escribir 'Es el instalar.sh del repositorio publico; no se ejecuta nada mas. Puede pedir sudo y abrir un inicio de sesion de GitHub.'
if (-not (Confirmar 'Ejecutar ahora?')) { Escribir 'No se ejecuto nada.'; return }
Correr-Linux $ComandoLinux $false | Out-Null
$salida = $script:CodigoWsl
if ($salida -ne 0) {
    Escribir ''
    Escribir ('El comando de Linux termino con codigo ' + $salida + '. Lee el mensaje de arriba; puedes volver a ejecutar el mismo comando.')
    return
}

# ---------- 7. avisos honestos ----------
Escribir ''
Escribir 'Listo. Para seguir trabajando abre Ubuntu (menu Inicio, o escribe wsl en PowerShell) y usa el terminal de Ubuntu.'
Escribir 'Avisos:'
Escribir '  - Docker Desktop: para usar docker dentro de Ubuntu activa la integracion con WSL (Settings, Resources, WSL integration).'
Escribir '  - El claude de Windows no es el de Ubuntu: el agente se instala por separado en cada sistema. Instalalo dentro de Ubuntu.'
Escribir '  - Trabaja siempre dentro del directorio personal de Linux, no en las carpetas de Windows (son lentas y rompen permisos).'
