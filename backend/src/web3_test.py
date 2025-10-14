from web3 import Web3

# Connect to local Hardhat node
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

if not w3.is_connected():
    print("Failed to connect to Hardhat node.")
    exit()

# Get the latest block number
latest_block_number = w3.eth.get_block("latest").get("number", 0)
print(f"Latest block number: {latest_block_number}\n")

# Iterate through all blocks
for block_num in range(latest_block_number + 1):
    block = w3.eth.get_block(block_num, full_transactions=True)
    
    block_number = block.get("number", 0)
    block_hash = block.get("hash", b"").hex() if block.get("hash") else ""
    timestamp = block.get("timestamp", 0)
    gas_used = block.get("gasUsed", 0)
    transactions = block.get("transactions", [])
    
    print(f"Block #{block_number}")
    print(f"  Hash: {block_hash}")
    print(f"  Timestamp: {timestamp}")
    print(f"  Gas used: {gas_used}")
    print(f"  Transactions: {len(transactions)}")
    
    for tx in transactions:
    # If tx is an AttributeDict
        tx_hash = getattr(tx, "hash", None)
        if tx_hash:
            tx_hash = tx_hash.hex()
        tx_from = getattr(tx, "from", "")
        tx_to = getattr(tx, "to", "")
        value = w3.from_wei(getattr(tx, "value", 0), 'ether')
        print(f"    Tx Hash: {tx_hash}, From: {tx_from}, To: {tx_to}, Value: {value} ETH")

    print("-" * 60)
