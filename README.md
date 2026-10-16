# OpenMPTCProuter VPS 0.1163-3K

Release stabile abbinata al [client v0.64.2-3K](https://github.com/Brazzo978/openmptcprouter/releases/tag/v0.64.2-3K). Installazione su **Debian 13 amd64 con CPU x86-64-v3**, come root. Il comando scarica il bundle completo e ne verifica lo SHA-256 prima di eseguire l'installer:

```sh
workdir=$(mktemp -d) && wget -O "$workdir/vps.tar.gz" https://github.com/Brazzo978/openmptcprouter-vps/releases/download/v0.1163-3K/openmptcprouter-vps-0.1163-3K.tar.gz && echo "5cfffea16a826a678b5fead2da7e8647aa062de7da0f1f49a6723e8546a893a7  $workdir/vps.tar.gz" | sha256sum -c - && tar -xzf "$workdir/vps.tar.gz" -C "$workdir" && cd "$workdir/openmptcprouter-vps-0.1163-3K" && ./run-vps-3k.sh install
```

L'installazione modifica rete, servizi e kernel. Le dipendenze Debian richiedono accesso APT. Al termine **riavviare la VPS** per usare il kernel incluso; SSH usa la porta **65222**. La configurazione generata per collegare il router è in `/root/openmptcprouter_config.txt`; il profilo per PC/telefono è in `/root/wireguard-client.conf`.

## Funzioni

- Kernel e headers **6.18.41-20261013.x64v3-omr-3k**, congelati nella release; **BBRv3 (`bbr`) predefinito**, 18 congestion control e varianti NanBBR.
- **21 pacchetti OMR congelati** e verificati con SHA-256. Kernel, pacchetti e API inclusi nel bundle; nessun download OMR necessario dai repository di Ysurac durante l'installazione verificata. Le dipendenze del sistema operativo provengono da Debian.
- MQVPN nativo **0.16.2-3k2**, supporto FEC/XOR/RSC/PKM compilato e routing dei prefissi LAN. Il FEC a runtime resta configurabile.
- IP del router primario **10.255.220.2** come default quando libero; configurazioni esplicite ed eventuali altri utenti preservati.
- API **0.18+20261016-3k4**, log diagnostici autenticati e redatti, TCP reverse forwarding tramite XRay separato e tunnel MQVPN.
- WireGuard remoto: accesso alla GUI OMR, LAN negata di default e abilitabile dalla checkbox del client o tramite helper/API VPS. Il full tunnel IPv4 `AllowedIPs = 0.0.0.0/0` può navigare con l'IP pubblico della VPS senza abilitare la LAN.
- Rimosse le API e la funzione di backup del router sulla VPS; aggiornamenti automatici OMR bloccati per rispettare il congelamento della build.

## Verifiche

Installazione da snapshot pulito Debian 13 conclusa con exit 0, riavvio nel kernel congelato e controllo di tutti i 21 pacchetti. **67 verifiche live superate**: 31 per installazione/API/servizi, 8 sul vero motore MQVPN con handshake e traffico verso una LAN di prova, 28 su WireGuard con HTTPS/DNS esterni, accesso GUI, blocco LAN, abilitazione esplicita e revoca anche di connessioni già aperte. Il report aggiunge un controllo sull'identità dell'archivio: **68 controlli complessivi**. Suite API: **1042 test superati, 9 saltati**.

SHA-256 del bundle effettivamente installato e pubblicato: `5cfffea16a826a678b5fead2da7e8647aa062de7da0f1f49a6723e8546a893a7`.

Il collaudo WireGuard usa una GUI/LAN simulata; il routing nativo MQVPN è stato verificato separatamente con pacchetti reali. Il precedente client fisico fibra + 5G è stato cancellato dall'utente e non è stato riabbinato dopo l'installazione pulita. Le prove precedenti sul client reale e gli inoltri TCP sono documentate nella release client. Non è stato eseguito un benchmark controllato del throughput aggregato né dimostrata la stabilità XRay di lungo periodo.

## Sorgenti e installazione

Branch predefinito: [`omr-vps-0.1163-3K`](https://github.com/Brazzo978/openmptcprouter-vps/tree/omr-vps-0.1163-3K). Il tag `v0.1163-3K` identifica il codice del bundle verificato; il branch contiene anche queste istruzioni di installazione. Un semplice clone non include tutti i binari congelati: usare il comando sopra o il bundle completo della release.

Per la procedura manuale e i dettagli WireGuard vedere [README-3K.md](https://github.com/Brazzo978/openmptcprouter-vps/blob/omr-vps-0.1163-3K/README-3K.md). Verificare gli altri asset con `SHA256SUMS-vps-0.1163-3K`.

