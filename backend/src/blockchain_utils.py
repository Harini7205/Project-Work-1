from web3 import Web3
import json, os
from dotenv import load_dotenv

load_dotenv()

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:7545")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
ABI_PATH = "./AccessRegistry.json"

w3 = Web3(Web3.HTTPProvider(RPC_URL))


def _load_contract():
    with open(ABI_PATH) as f:
        abi = json.load(f)

    return w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=abi
    )

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
def _b32(x):
    """Convert hex / bytes → bytes32"""
    if isinstance(x, bytes):
        return x
    if isinstance(x, str):
        if x.startswith("0x"):
            x = x[2:]
        return bytes.fromhex(x.zfill(64))
    raise ValueError("Invalid bytes32")


# ------------------------------------------------------------
# IDENTITY
# ------------------------------------------------------------
def register_identity(eth_address: str, pubkey_bytes: bytes):
    """
    Prepares tx for:
    registerIdentity(bytes pubKey)
    """
    contract = _load_contract()
    eth_address = Web3.to_checksum_address(eth_address)

    tx = contract.functions.registerIdentity(
        pubkey_bytes
    ).build_transaction({
        "from": eth_address,
        "nonce": w3.eth.get_transaction_count(eth_address),
        "gas": 200_000,
        "chainId": w3.eth.chain_id,
    })

    return tx


# ------------------------------------------------------------
# RECORDS
# ------------------------------------------------------------
def store_record(eth_address, record_id, ch_hash, cid, consent):
    contract = _load_contract()
    eth_address = Web3.to_checksum_address(eth_address)

    tx = contract.functions.storeRecord(
        _b32(record_id),
        _b32(ch_hash),
        cid,
        bool(consent),
    ).build_transaction({
        "from": eth_address,
        "nonce": w3.eth.get_transaction_count(eth_address),
        "gas": 500_000,
        "chainId": w3.eth.chain_id,
    })

    return tx


def update_record(eth_address, record_id, cid, ch_hash):
    contract = _load_contract()
    eth_address = Web3.to_checksum_address(eth_address)

    tx = contract.functions.updateRecord(
        _b32(record_id),
        _b32(ch_hash),
        cid
    ).build_transaction({
        "from": eth_address,
        "nonce": w3.eth.get_transaction_count(eth_address),
        "gas": 500_000,
        "chainId": w3.eth.chain_id,
    })

    return tx


def get_record_by_id(record_id: str):
    contract = _load_contract()
    owner, h, encryptedCid, consent, timestamp = contract.functions.getRecord(
        _b32(record_id)
    ).call()

    return {
        "owner": owner,
        "h": h.hex(),
        "encryptedCid": encryptedCid,
        "consent": consent,
        "timestamp": timestamp,
    }


def toggle_consent_tx(eth_address, record_id, active):
    contract = _load_contract()
    eth_address = Web3.to_checksum_address(eth_address)

    tx = contract.functions.toggleConsent(
        _b32(record_id),
        bool(active)
    ).build_transaction({
        "from": eth_address,
        "nonce": w3.eth.get_transaction_count(eth_address),
        "gas": 300_000,
        "chainId": w3.eth.chain_id,
    })

    return tx


# ------------------------------------------------------------
# ACCESS REQUESTS
# ------------------------------------------------------------
def submit_access_request(
    doctor,
    patient,
    record_id,
    role,
    timestamp,
    nonce,
    v, r, s,
    ttl
):
    contract = _load_contract()

    doctor  = Web3.to_checksum_address(doctor)
    patient = Web3.to_checksum_address(patient)

    tx = contract.functions.requestAccess(
        patient,
        _b32(record_id),
        int(role),
        int(timestamp),
        int(nonce),
        int(v),
        _b32(r),
        _b32(s),
        int(ttl)
    ).build_transaction({
        "from": doctor,
        "nonce": w3.eth.get_transaction_count(doctor),
        "gas": 800_000,
        "chainId": w3.eth.chain_id,
    })

    return tx


def check_token_valid(token: str):
    contract = _load_contract()
    return contract.functions.tokenValid(_b32(token)).call()

def get_record_id_by_owner(patient_address: str):
    contract = _load_contract()
    patient_address = Web3.to_checksum_address(patient_address)
    record_id = contract.functions.getRecordIdByOwner(
        patient_address
    ).call()

    if record_id == Web3.to_bytes(0):
        return None

    return record_id.hex()



# ------------------------------------------------------------
# EVENTS (NO NAMES — resolved via SQLite)
# ------------------------------------------------------------
def _topic0(sig: str):
    return Web3.keccak(text=sig).hex()


def _topic_addr(addr: str):
    return Web3.to_hex(
        Web3.to_bytes(hexstr=Web3.to_checksum_address(addr)).rjust(32, b"\x00")
    )


def fetch_access_logs_for_doctor(doctor: str):
    registry = _load_contract()
    doctor = Web3.to_checksum_address(doctor)

    logs = registry.events.AccessRequested.get_logs(
        from_block=0,
        to_block="latest",
        argument_filters={
            "provider": doctor
        }
    )

    return logs


def fetch_access_logs_for_patient(patient: str):
    registry = _load_contract()
    patient = Web3.to_checksum_address(patient)

    logs = w3.eth.get_logs({
        "address": registry.address,
        "fromBlock": 0,
        "toBlock": "latest",
        "topics": [
            _topic0("AccessRequested(address,address,bytes32,bytes32,uint64)"),
            None,
            _topic_addr(patient),
            None
        ]
    })

    return [
        {
            "doctor_address": ev["args"]["provider"],
            "patient_address": ev["args"]["patient"],
            "record_id": ev["args"]["recordId"].hex(),
            "token": ev["args"]["token"].hex(),
            "expiresAt": int(ev["args"]["expiresAt"]),
        }
        for ev in map(
            registry.events.AccessRequested().process_log, logs
        )
    ]
