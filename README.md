Host.py starts the crypto node and hosts the blockchain and wallets, 

Client.py mines zQoin crypto, as well as sends/recieves to wallets(next step!)

Calculate.py calculates the maximum supply of coins based on difficulty vars

Includes [DotSlashVerify](https://github.com/dotslashCosmic/DotSlashVerify) hashes for the files

Stupid little project I felt like making today, might make something out of it
- I'm going to try to make an actual cryptocurrency, gl me
- 7/27 got the mining pool woo

Requires $ pip install flask & tkinter

To customize:
- in client.py, change: coin_name, short_name, client_port, host_port, server_ip, wallet_list, and block_flood_limit 
- sha3-512 client.py
- in host.py, change: client_port, host_port, coin_name, reward, time_between_rewards, consensus_count, genesis_token, and client_version with the client.py sha3-512 hash
