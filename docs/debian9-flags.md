# Flag e variabili di `debian9-x86_64.sh`

Questa pagina riassume le variabili configurabili dichiarate all'inizio dello script `debian9-x86_64.sh`, indicando il valore di default e l'effetto pratico che hanno sul flusso di installazione o configurazione del VPS OpenMPTCProuter.

## Flag di comportamento principali

| Variabile | Valore predefinito | Effetto |
| --- | --- | --- |
| `UPSTREAM` | `no` | Impostandolo a `yes` lo script forza `SOURCES=yes`, compila strumenti MPTCP direttamente dal sorgente e abilita `mptcpize` sui servizi chiave (iperf3, omr-admin, v2ray e openvpn) per sfruttare il kernel MPTCP appena installato.【F:debian9-x86_64.sh†L9-L35】【F:debian9-x86_64.sh†L386-L410】【F:debian9-x86_64.sh†L665-L667】【F:debian9-x86_64.sh†L818-L842】【F:debian9-x86_64.sh†L1113-L1115】 |
| `OBFS` | `yes` | Controlla l'installazione del plugin `simple-obfs`: con `yes` viene installato (da sorgente se `SOURCES=yes`, altrimenti via pacchetto); con `no` lo script rimuove ogni riferimento al plugin dalla configurazione di Shadowsocks.【F:debian9-x86_64.sh†L15-L16】【F:debian9-x86_64.sh†L744-L807】 |
| `V2RAY_PLUGIN` | `yes` | Se attivo installa il plugin `v2ray-plugin` (ancora una volta scegliendo tra compilazione e pacchetto in base a `SOURCES`); se disattivato, e contemporaneamente `OBFS=no`, vengono eliminati i campi `plugin` dal JSON di Shadowsocks.【F:debian9-x86_64.sh†L16-L17】【F:debian9-x86_64.sh†L744-L811】 |
| `V2RAY` | `yes` | Determina se installare il servizio server V2Ray, generando il file `v2ray-server.json`, attivando il servizio e (in modalità `UPSTREAM=yes`) abilitando `mptcpize` anche su V2Ray.【F:debian9-x86_64.sh†L17-L18】【F:debian9-x86_64.sh†L818-L843】 |
| `UPDATE` | `yes` | Abilitando il “modo aggiornamento” lo script rileva un’installazione esistente e riutilizza le credenziali/shadow config invece di rigenerarle da zero.【F:debian9-x86_64.sh†L20-L21】【F:debian9-x86_64.sh†L232-L241】【F:debian9-x86_64.sh†L678-L706】 |
| `TLS` | `yes` | Gestisce la generazione/rinnovo del certificato ACME per omr-admin e V2Ray. Se si abilita il mirror cinese (`CHINA=yes`) viene forzato a `no`, mentre con `yes` tenta l’emissione del certificato e collega i file `.cer/.key` a omr-admin.【F:debian9-x86_64.sh†L21-L22】【F:debian9-x86_64.sh†L264-L286】【F:debian9-x86_64.sh†L1342-L1362】 |
| `OMR_ADMIN` | `yes` | Controlla l’installazione del pannello `omr-vps-admin`: lo script installa dipendenze, pacchetto (o sorgente), aggiorna le credenziali, genera il certificato locale e abilita i servizi systemd associati, includendo la variante IPv6 quando presente.【F:debian9-x86_64.sh†L22-L24】【F:debian9-x86_64.sh†L547-L669】 |
| `MLVPN` | `yes` | Attiva l’installazione e la (eventuale) compilazione di MLVPN, popola la configurazione con la password generata e abilita il relativo servizio di bonding.【F:debian9-x86_64.sh†L25-L26】【F:debian9-x86_64.sh†L851-L907】 |
| `UBOND` | `no` | Se impostato a `yes` compila e installa UBOND, genera la configurazione (inserendo `UBOND_PASS`) e abilita il servizio di bonding; lasciandolo `no` lo salta del tutto.【F:debian9-x86_64.sh†L27-L28】【F:debian9-x86_64.sh†L920-L970】 |
| `OPENVPN` | `yes` | Controlla l’installazione di OpenVPN, inclusi EasyRSA, i profili bonding e l’eventuale abilitazione di `mptcpize` sul servizio primario quando `UPSTREAM=yes`.【F:debian9-x86_64.sh†L29-L30】【F:debian9-x86_64.sh†L1018-L1123】 |
| `DSVPN` | `yes` | Abilita l’installazione del pacchetto DSVPN, la creazione del file chiave e l’attivazione dell’unità `dsvpn-server@dsvpn0.service`.【F:debian9-x86_64.sh†L30-L31】【F:debian9-x86_64.sh†L1154-L1176】 |
| `WIREGUARD` | `yes` | Decide se installare e configurare WireGuard (server, client e file di esempio) abilitando le unità `wg-quick`.【F:debian9-x86_64.sh†L31-L32】【F:debian9-x86_64.sh†L966-L1011】 |
| `SOURCES` | `no` (o `yes` se `UPSTREAM=yes`) | Quando vale `yes` lo script preferisce compilare da sorgente componenti come Shadowsocks, simple-obfs, v2ray-plugin e persino il pannello omr-admin; con `no` scarica i pacchetti `.deb` precompilati.【F:debian9-x86_64.sh†L32-L35】【F:debian9-x86_64.sh†L414-L459】【F:debian9-x86_64.sh†L744-L807】【F:debian9-x86_64.sh†L604-L626】 |
| `NOINTERNET` | `no` | Se impostato a `yes` disabilita le funzioni “internet sharing” nel JSON di omr-admin, utile in ambienti senza connettività esterna.【F:debian9-x86_64.sh†L36-L37】【F:debian9-x86_64.sh†L657-L659】 |
| `REINSTALL` | `yes` | Variabile prevista per forzare reinstallazioni ma non utilizzata nello script: modificarla non ha effetto attualmente.【F:debian9-x86_64.sh†L37-L38】 |
| `SPEEDTEST` | `yes` | Abilita la creazione del file `test.img` da 1 GiB per il servizio di speedtest interno di omr-server.【F:debian9-x86_64.sh†L38-L39】【F:debian9-x86_64.sh†L1371-L1378】 |
| `LOCALFILES` | `no` | Con `no` scarica script e template dal sito ufficiale, mentre con `yes` copia i file locali dal repository (utile se si mantiene un mirror locale o si lavora offline).【F:debian9-x86_64.sh†L39-L41】【F:debian9-x86_64.sh†L369-L374】【F:debian9-x86_64.sh†L672-L741】【F:debian9-x86_64.sh†L1220-L1245】 |
| `CHINA` | `no` | Quando settato a `yes` e insieme a `USE_OMR_REPO=yes`, forza l’uso di mirror locali Git, abilita `LOCALFILES=yes` e disabilita `TLS` per evitare chiamate esterne durante l’installazione.【F:debian9-x86_64.sh†L69-L71】【F:debian9-x86_64.sh†L264-L286】 |
| `USE_OMR_REPO` | `no` (impostato nel sorgente) | Se cambiato in `yes` aggiunge i repository APT OpenMPTCProuter, con comportamento diverso per `CHINA=yes`, e lancia un `apt-get update` dedicato.【F:debian9-x86_64.sh†L261-L310】 |
| `FORCE_REINSTALL` | `no` | Passato alla funzione `install_deb_from_url`; con `yes` forza la reinstallazione dei pacchetti proprietari anche se la versione installata è uguale o più recente.【F:debian9-x86_64.sh†L71-L72】【F:debian9-x86_64.sh†L147-L158】 |

## Credenziali e identificativi generati

| Variabile | Valore predefinito | Utilizzo |
| --- | --- | --- |
| `SHADOWSOCKS_PASS` | Stringa casuale base64 | Usato per popolare `manager.json` (normalizzato per JSON) e ripristinato durante gli aggiornamenti per non perdere la chiave esistente.【F:debian9-x86_64.sh†L10-L11】【F:debian9-x86_64.sh†L678-L706】【F:debian9-x86_64.sh†L692-L699】 |
| `GLORYTUN_PASS` | Stringa esadecimale maiuscola casuale | Riutilizzato/creato nei file `tun0.key` di glorytun UDP e TCP per mantenere sincronizzate le chiavi tra reinstallazioni.【F:debian9-x86_64.sh†L11-L12】【F:debian9-x86_64.sh†L1134-L1204】 |
| `DSVPN_PASS` | Stringa esadecimale maiuscola casuale | Salvato in `/etc/dsvpn/dsvpn0.key` quando DSVPN è attivo, garantendo un segreto coerente.【F:debian9-x86_64.sh†L12-L13】【F:debian9-x86_64.sh†L1154-L1175】 |
| `OMR_ADMIN_PASS` | Stringa esadecimale maiuscola casuale | Inserita in `omr-admin-config.json`, riutilizzata se esiste già e mostrata nei messaggi finali come chiave server.【F:debian9-x86_64.sh†L23-L24】【F:debian9-x86_64.sh†L612-L656】【F:debian9-x86_64.sh†L1409-L1494】 |
| `OMR_ADMIN_PASS_ADMIN` | Stringa esadecimale maiuscola casuale | Aggiorna la password dell’utente “admin” di omr-admin e viene preservata se già impostata.【F:debian9-x86_64.sh†L24-L25】【F:debian9-x86_64.sh†L612-L656】【F:debian9-x86_64.sh†L1409-L1494】 |
| `MLVPN_PASS` | Stringa base64 casuale | Sostituisce il placeholder nella configurazione `mlvpn0.conf` quando MLVPN viene installato per la prima volta.【F:debian9-x86_64.sh†L26-L27】【F:debian9-x86_64.sh†L894-L899】 |
| `UBOND_PASS` | Stringa base64 casuale | Inserito in `ubond0.conf` durante la generazione della configurazione iniziale di UBOND.【F:debian9-x86_64.sh†L28-L29】【F:debian9-x86_64.sh†L935-L950】 |
| `V2RAY_UUID` | UUID casuale | Sostituisce il placeholder `V2RAY_UUID` nel JSON di configurazione del server V2Ray quando viene creato per la prima volta.【F:debian9-x86_64.sh†L18-L19】【F:debian9-x86_64.sh†L825-L828】 |

## Parametri auto-rilevati

| Variabile | Valore predefinito | Note |
| --- | --- | --- |
| `NBCPU` | Numero di CPU logiche (`grep -c '^processor'`) | Determina quante istanze Shadowsocks vengono configurate nel `manager.json` e quante unità vengono abilitate.【F:debian9-x86_64.sh†L13-L14】【F:debian9-x86_64.sh†L693-L723】 |
| `INTERFACE` | Interfaccia del default gateway IPv4 | Sostituisce `eth0` nei file di Shorewall/ Shorewall6 per adattare il firewall all’interfaccia reale del VPS.【F:debian9-x86_64.sh†L39-L41】【F:debian9-x86_64.sh†L1276-L1317】 |
| `VPS_DOMAIN` | Risolto da `hostname.openmptcprouter.com` | Utilizzato per emettere certificati ACME e collegarli a omr-admin/V2Ray quando `TLS=yes`.【F:debian9-x86_64.sh†L64-L67】【F:debian9-x86_64.sh†L1342-L1362】 |
| `VPS_PUBLIC_IP` | Ottenuto da `ip.openmptcprouter.com` | Inserito nel file client WireGuard come endpoint pubblico di default.【F:debian9-x86_64.sh†L65-L67】【F:debian9-x86_64.sh†L998-L1007】 |

## Altri valori di contesto

| Variabile | Valore predefinito | Ruolo |
| --- | --- | --- |
| `UPDATE_OS` | `yes` | Placeholder per aggiornamenti di sistema: al momento non viene referenziato più avanti nello script.【F:debian9-x86_64.sh†L19-L20】 |
| `DEFAULT_USER` | `openmptcprouter` | Sostituisce il nome utente predefinito nel file `omr-admin-config.json` generato da omr-admin.【F:debian9-x86_64.sh†L63-L64】【F:debian9-x86_64.sh†L654-L656】 |
| `VPSPATH` | `server` | Concatenato con `VPSURL` per scaricare script e template da remoto.【F:debian9-x86_64.sh†L65-L67】【F:debian9-x86_64.sh†L369-L741】 |
| `VPSURL` | `https://www.openmptcprouter.com/` | Host principale da cui scaricare kernel, servizi e template quando `LOCALFILES=no`.【F:debian9-x86_64.sh†L67-L68】【F:debian9-x86_64.sh†L369-L741】 |
| `REPO` | `repo.openmptcprouter.com` | Dominio usato per impostare i repository APT personalizzati quando `USE_OMR_REPO=yes`.【F:debian9-x86_64.sh†L68-L69】【F:debian9-x86_64.sh†L288-L307】 |

