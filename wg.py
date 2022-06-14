#!/usr/bin/python
"""Creating wireguard configuration."""

from ipaddress import IPv4Address, ip_network
import os.path
from random import sample
import subprocess

used_ips: set[IPv4Address] = {
    IPv4Address('10.0.0.1'),
    IPv4Address('10.0.0.2')
}

class WireGuardConfig:
    """Manage config files."""

    __client_name: str
    __selected_ip: IPv4Address
    MASK_BITS: int = 24
    SERVER_ADRESS: str = '45.142.215.232'
    HOSTS_NET: str = '10.0.0.0'
    SERVER_PORT: int = 51820
    CONFIGS_PATH: str = '/etc/wireguard/clients'
    SERVER_PUBLIC_KEY_PATH: str = '/etc/wireguard/server/server.key.pub'

    def __init__(self, client_name: str):
        """Select unused ip and init inner fields."""
        self.__client_name = client_name
        available_ips = set(ip_network(self.HOSTS_NET + '/' +
                                       str(self.MASK_BITS)).hosts()) - used_ips
        if len(available_ips) > 0:
            self.__selected_ip = sample(available_ips, 1)[0]
        else:
            self.__selected_ip = None

    def exists(self) -> bool:
        """Check that user config file exists."""
        return (os.path.isfile(self.__get_public_key_path()) and
                os.path.isfile(self.__get_private_key_path()) and
                os.path.isfile(self.get()))

    def get(self) -> str:
        """Return path to config file."""
        return self.CONFIGS_PATH + '/' + self.__client_name + '.conf'

    def address(self) -> IPv4Address:
        """Return selected address."""
        return self.__selected_ip

    # pylint: disable=W0703,W0717 # Disable catching general Exception and big try-except clause.
    def create(self) -> tuple[bool, str]:
        """Create new config file for user.

        Return tuple where first value is the proccess success,
        but the second is the error message.
        """
        if self.__selected_ip is None:
            return (False, "No available ip for client!")
        try:
            self.__generate_keys()
            private = WireGuardConfig.__read_file(self.__get_private_key_path())
            public  = WireGuardConfig.__read_file(self.__get_public_key_path())
            self.__fill_out_config(private,
                                   WireGuardConfig.__read_file(self.SERVER_PUBLIC_KEY_PATH))
            self.__add_client_key_to_server(public)
            used_ips.add(self.address())
        except Exception as exs:
            return (False, str(exs))
        return (True, self.get())

    def __fill_out_config(self, client_private: str, server_public: str):
        """Fill config file for client."""
        with open(self.get(), 'w', encoding='utf-8') as config:
            config.write('[Interface]\n')
            config.write(f'PrivateKey = {client_private}\n')
            config.write(f'Address = {format(self.__selected_ip)}\n')
            config.write('\n')
            config.write('[Peer]\n')
            config.write(f'PublicKey = {server_public}\n')
            config.write(f'Endpoint = {self.SERVER_ADRESS}:{self.SERVER_PORT}\n')
            config.write('AllowedIPs = 0.0.0.0/0')

    def __get_public_key_path(self) -> str:
        """Return path to public key."""
        return self.CONFIGS_PATH + '/' + self.__client_name + '.key.pub'

    def __get_private_key_path(self) -> str:
        """Return path to private key."""
        return self.CONFIGS_PATH + '/' + self.__client_name + '.key'

    def __generate_keys(self) -> None:
        """Run bash scripts to generate keys."""
        if subprocess.getstatusoutput(f"mkdir -p {self.CONFIGS_PATH}")[0]:
            raise Exception("Can not create directory for config!")
        if subprocess.getstatusoutput(self.__genkeys_cmd())[0]:
            raise Exception("Can not generate keys!")

    def __add_client_key_to_server(self, client_public: str):
        """Add client’s public key and IP address to the server."""
        if subprocess.getstatusoutput(f"wg set wg0 peer {client_public} "
                                      f"allowed-ips {format(self.__selected_ip)}")[0]:
            raise Exception("Can not add client ip to server!")

    @classmethod
    def __read_file(cls, path: str) -> str:
        """Read file contents."""
        with open(path, 'r', encoding='utf-8') as file_descriptor:
            return file_descriptor.read().strip()

    def __genkeys_cmd(self) -> str:
        """Bash command to create keys."""
        cmd_create_keys: str = "wg genkey | "
        cmd_create_keys += f"tee {self.CONFIGS_PATH}/{self.__client_name}.key | "
        cmd_create_keys += "wg pubkey | "
        cmd_create_keys += f"tee {self.CONFIGS_PATH}/{self.__client_name}.key.pub"
        return cmd_create_keys
