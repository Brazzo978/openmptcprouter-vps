
This fork focuses on bringing back the ability for all the user to install previus version of the vps script , to get full compatibility with older client with version 0.59.1 this uses the original package from 1028-era vps installation script , some provided by the openmptcprouter repo and some from this fork in the pack folder.

Currently the only thing changed from the original 1028 stock is the glorytun tcp version , from omr-glorytun-tcp_0.0.35-3_amd64.deb to omr-glorytun-tcp_0.0.35-6_amd64.deb which is the latest , if problems arise i will patch to use the original one.

The script has been fully cleaned from useless feature like upstream kernel.
The script now runs only and i say ONLY on debian 11 by default , it will not run on debian 12 or later , or debian 10/9 , because upgrading from those older version made use of dead dependencies and is now harder , so get a vps with debian 11 already and this will work.

To install just Run this command.
> ```bash
> curl -sL https://raw.githubusercontent.com/Brazzo978/openmptcprouter-vps/omr-vps-0.1028-def/debian9-x86_64.sh | bash
> ```



REGULAR INSTALL STUFF : 
# OpenMPTCProuter VPS scripts

All scripts needed to install OpenMPTCProuter VPS.

This is the VPS part of [OpenMPTCProuter](https://www.openmptcprouter.com/), a solution to aggregate multiple internet connections.
 
* ```debian9-x86_64.sh```: The main script install ShadowSocks, Glorytun TCP, Glorytun UDP, Shorewall, the MPTCP kernel and can install OpenVPN
* ```debian9-x86_64-mlvpn.sh```: Script to install MLVPN
* ```config.json```: shadowsocks config
* ```/shorewall4```: shorewall default configuration
* ```/shorewall6```: shorewall6 default configuration
* ```glorytun-tcp-run```: script to run glorytun with configuration parameters
* ```glorytun-tcp@.service.in```: glorytun systemd service
* ```glorytun.network```: glorytun systemd network (for DHCP)
* ```glorytun-udp-run```: script to run glorytun UDP with configuration parameters
* ```glorytun-udp.network```: glorytun UDP systemd network (for DHCP)
* ```glorytun-udp@.service.in```: glorytun UDP systemd service
* ```mlvpn.network```: MLVPN systemd network (for DHCP)
* ```mlvpn0.conf```: MLVPN default config
* ```omr-6in4-service```: Script used to make 6in4 tunnel always up and detect ip used by OpenMPTCProuter to config Shorewall
* ```omr-6in4.service.in```: Systemd service to run the script
* ```openvpn-tun0.cnf```: OpenVPN default config
* ```openvpn.network```: OpenVPN systemd network (for DHCP)
* ```shadowsocks.conf```: shadowsocks sysctl.d optimization and mptcp config
* ```tun0.glorytun```: glorytun default configuration
* ```tun0.glorytun-udp```: glorytun default configuration
* ```update-grub.sh```: Script used to check if MPTCP kernel is the default
