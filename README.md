Host.py starts the crypto node and hosts the blockchain

Client.py can make wallets, and mine zQoin crypto, as well as send/recieve

Calculate.py calculates the maximum supply of coins based on difficulty vars

Includes [DotSlashVerify](https://github.com/dotslashCosmic/DotSlashVerify) hashes for the files

Stupid little project I felt like making today, might make something out of it
- I'm going to try to make an actual cryptocurrency, gl me

Requires $ pip install flask & tkinter

To customize:
- in client.py, change: coin_name, short_name, client_port, host_port
- sha3-512 client.py
- in host.py, change: client_port, host_port, full_name(coin_name), and client_version with the client.py sha3-512 hash
