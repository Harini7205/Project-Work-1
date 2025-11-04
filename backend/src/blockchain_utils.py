from web3 import Web3
from eth_account import Account
import json, os
from dotenv import load_dotenv

load_dotenv()

RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:7545")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
PRIVATE_KEY = os.getenv("SENDER_PRIVATE_KEY")
ABI_PATH = "./KeyRegistry.json"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
acct = Account.from_key(PRIVATE_KEY)

def _load_contract():
    abi = json.load(open(ABI_PATH))
    return w3.eth.contract(address=Web3.to_checksum_address(str(CONTRACT_ADDRESS)), abi=abi)

def register_record(cid: str, ch_hash: str, patient_id: str):
    contract = _load_contract()
    h_bytes32 = bytes.fromhex(ch_hash[:64])
    nonce = w3.eth.get_transaction_count(acct.address)
    tx = contract.functions.storeData(h_bytes32, cid).build_transaction({
        "chainId": w3.eth.chain_id,
        "from": acct.address,
        "nonce": nonce,
        "gas": 3000000,
        "gasPrice": w3.to_wei('1', 'gwei')
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return tx_hash.hex()

def redact_record(patient_id, old_cid, new_cid, new_hash):
    contract = _load_contract()
    h_bytes32 = bytes.fromhex(new_hash[:64])
    nonce = w3.eth.get_transaction_count(acct.address)
    tx = contract.functions.storeData(h_bytes32, new_cid).build_transaction({
        "chainId": w3.eth.chain_id,
        "from": acct.address,
        "nonce": nonce,
        "gas": 3000000,
        "gasPrice": w3.to_wei('1', 'gwei')
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return tx_hash.hex()
