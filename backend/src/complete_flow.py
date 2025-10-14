# backend/src/flow_register_and_store.py
import json
from pathlib import Path
from dotenv import load_dotenv

from web3 import Web3
from eth_account import Account
from key_generation.ecc import generate_ecc_key_pair
from ipfs.ipfs_helper import upload_to_ipfs, download_from_ipfs
from chameleon_hash.ch_secp256k1 import encode_message, ch_hash, _rand_scalar  # re-use helper
import os

BASE = Path(__file__).resolve().parent
OUT = BASE.joinpath("outputs")
IN = BASE.joinpath("inputs/sample.pdf")
OUT.mkdir(exist_ok=True)
load_dotenv()  

# --- CONFIG ---
HARDHAT_RPC = "http://127.0.0.1:8545"  
ABI_PATH = BASE.joinpath("KeyRegistry.json")  
CONTRACT_ADDRESS = os.environ.get("CONTRACT_ADDRESS")  
SENDER_PRIVATE_KEY = os.environ.get('SENDER_PRIVATE_KEY')  

w3 = Web3(Web3.HTTPProvider(HARDHAT_RPC))
acct = Account.from_key(SENDER_PRIVATE_KEY)

def load_contract():
    abi = json.loads(open(ABI_PATH).read())
    return w3.eth.contract(address=Web3.to_checksum_address(str(CONTRACT_ADDRESS)), abi=abi)

def register_pubkey_and_store(pk_bytes: bytes, cid: str, ch_hex: str):
    contract = load_contract()

    # 1) registerKey(bytes pubKey)
    nonce = w3.eth.get_transaction_count(acct.address)
    tx1 = contract.functions.registerKey(pk_bytes).build_transaction({
        "chainId": w3.eth.chain_id,
        "from": acct.address,
        "nonce": nonce,
        "gas": 3000000,
        "gasPrice": w3.to_wei('1', 'gwei')
    })
    signed1 = acct.sign_transaction(tx1)
    tx_hash1 = w3.eth.send_raw_transaction(signed1.raw_transaction)
    print("registerKey tx sent:", tx_hash1.hex())
    w3.eth.wait_for_transaction_receipt(tx_hash1)
    print("Registered public key.")

    # 2) storeData(bytes32 h, string encryptedCid)
    # contract expects bytes32; our ch_hex is hex digest (64 chars). Convert to bytes32
    h_bytes32 = bytes.fromhex(ch_hex[:64]) if len(ch_hex) >= 64 else bytes.fromhex(ch_hex.rjust(64, "0"))
    nonce = w3.eth.get_transaction_count(acct.address)
    tx2 = contract.functions.storeData(h_bytes32, cid).build_transaction({
        "chainId": w3.eth.chain_id,
        "from": acct.address,
        "nonce": nonce,
        "gas": 3000000,
        "gasPrice": w3.to_wei('1', 'gwei')
    })
    signed2 = acct.sign_transaction(tx2)
    tx_hash2 = w3.eth.send_raw_transaction(signed2.raw_transaction)
    print("storeData tx sent:", tx_hash2.hex())
    w3.eth.wait_for_transaction_receipt(tx_hash2)
    print("Stored chameleon hash and CID.")

def main():
    # 0) sanity
    assert CONTRACT_ADDRESS != "<PUT_DEPLOYED_CONTRACT_ADDRESS_HERE>", "Set CONTRACT_ADDRESS in this file"
    assert SENDER_PRIVATE_KEY != "<HARDHAT_ACCOUNT_PRIVATE_KEY>", "Set a local account private key here"

    # 1) generate ECC keys (dev)
    sk, pk = generate_ecc_key_pair(save_to_disk=True)
    pk_bytes = Path(BASE.joinpath("outputs/pk.bin")).read_bytes()
    print("Saved pk.bin and sk.hex in outputs/", pk_bytes.hex())

    # 2) encrypt folder and upload to IPFS
    input_file = str(IN)  
    out_file = str(OUT.joinpath("stored_file.pdf"))
    
    cid = upload_to_ipfs(input_file)
    print("Uploaded to IPFS CID:", cid)
    with open(OUT.joinpath("cid.txt"), "w") as f:
        f.write(cid + "\n")

    download_from_ipfs(cid, out_file)  # test download + decrypt
    print("Decrypted file saved to:", out_file)    

    # 3) get (placeholder) proof bytes — replace with actual PLONK proof bytes later
    proof = b"\x00" * 96  # placeholder; replace with generated pi bytes
    identity = pk_bytes  # compressed public key bytes as identity
    msg = encode_message(proof, cid, True, identity)
    r = _rand_scalar()
    ch_hex, comp = ch_hash(msg, r, pk_bytes)
    print("Computed chameleon hash:", ch_hex)

    # Save outputs
    with open(OUT.joinpath("ch_hash.hex"), "w") as f:
        f.write(ch_hex + "\n")
    with open(OUT.joinpath("r.hex"), "w") as f:
        f.write(hex(r) + "\n")

    # 4) register + store on-chain
    register_pubkey_and_store(pk_bytes, cid, ch_hex)
    print("Done.")

if __name__ == "__main__":
    main()
