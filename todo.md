#Potential TODO List

## client.py
1. **Encrypt Private Keys**: Implement AES encryption for storing private keys in `wallet.json`.
2. **Secure Signing Algorithm**: Replace the current signing method with ECDSA.
3. **Use HTTPS**: Update the network communication to use HTTPS instead of HTTP.
4. **Input Validation**: Implement input validation checks for transaction amounts and addresses.
5. **Hierarchical Deterministic Wallets (HD Wallets)**: Implement HD wallets to generate a tree of keys from a single seed.
6. **Multi-Signature Transactions**: Support multi-signature transactions for enhanced security.
7. **Transaction Fee Calculation**: Implement dynamic transaction fee calculation based on network conditions.
8. **Address Reuse Prevention**: Ensure that new addresses are generated for each transaction to enhance privacy.
9. **BIP-39 Mnemonic Phrases**: Implement BIP-39 for generating mnemonic phrases for wallet backup and recovery.

### host.py
1. **Encrypt Blockchain Data**: Implement encryption for storing the blockchain in `blockchain.json` using a secure encryption library like `cryptography`.
2. **Use HTTPS**: Update the network communication to use HTTPS instead of HTTP.
3. **Proof of Work (PoW)**: Implement a PoW consensus algorithm to secure the network.
4. **Block Validation**: Implement comprehensive block validation rules to ensure the integrity of the blockchain.
5. **Peer-to-Peer (P2P) Network**: Implement a P2P network for decentralized communication between nodes.
6. **Transaction Pool**: Maintain a pool of unconfirmed transactions to be included in future blocks.
7. **UTXO Model**: Implement the UTXO (Unspent Transaction Output) model for tracking transaction outputs.
8. **Blockchain Pruning**: Implement blockchain pruning to reduce storage requirements by removing old, spent transaction data.
