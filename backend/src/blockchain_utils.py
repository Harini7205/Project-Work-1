from web3 import Web3
import json, os
from dotenv import load_dotenv

load_dotenv()

RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:7545")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
ABI_PATH = "./AccessRegistry.json"

w3 = Web3(Web3.HTTPProvider(RPC_URL))


def _load_contract():
    with open(ABI_PATH) as f:
        abi = json.load(f)

    return w3.eth.contract(
        address=Web3.to_checksum_address(str(CONTRACT_ADDRESS)),
        abi=abi
    )

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def _add_hex_prefix(x) -> str:
    if not x:
        return x
    x = str(x)
    return x if x.startswith("0x") else "0x" + x


def _b32(x):
    if isinstance(x, bytes):
        return x
    if isinstance(x, str):
        x = x.lower()
        if x.startswith("0x"):
            x = x[2:]
        return bytes.fromhex(x.zfill(64))
    raise ValueError("bad input for bytes32")

def register_identity(eth_address: str, pubkey_bytes: bytes, name: str):
    contract = _load_contract()
    eth_address = Web3.to_checksum_address(eth_address)

    tx = contract.functions.registerIdentity(
        pubkey_bytes, name
    ).build_transaction({
        "from": eth_address,
        "nonce": w3.eth.get_transaction_count(eth_address),
        "gas": 250000,
        "chainId": w3.eth.chain_id,
    })

    return tx

def store_record(eth_address, record_id, ch_hash, cid, consent):
    contract = _load_contract()
    eth_address = Web3.to_checksum_address(eth_address)

    rid = _b32(record_id)
    hh  = _b32(ch_hash)

    tx = contract.functions.storeRecord(
        rid,
        hh,
        cid,
        bool(consent),
    ).build_transaction({
        "from": eth_address,
        "nonce": w3.eth.get_transaction_count(eth_address),
        "gas": 500000,
        "chainId": w3.eth.chain_id,
    })

    return tx

def update_record(eth_address, record_id, cid, ch_hash):
    contract = _load_contract()
    eth_address = Web3.to_checksum_address(eth_address)

    rid = _b32(record_id)
    hh  = _b32(ch_hash)

    tx = contract.functions.updateRecord(
        rid,
        hh,
        cid
    ).build_transaction({
        "from": eth_address,
        "nonce": w3.eth.get_transaction_count(eth_address),
        "gas": 500000,
        "chainId": w3.eth.chain_id,
    })

    return tx
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
    rid     = _b32(record_id)

    if isinstance(r, str):
        r = _b32(r)
    if isinstance(s, str):
        s = _b32(s)

    tx = contract.functions.requestAccess(
        patient,     # ✅ correct arg1
        rid,         # ✅ correct arg2
        int(role),   # ✅ correct arg3
        int(timestamp),
        int(nonce),
        int(v),
        r,
        s,
        int(ttl)
    ).build_transaction({
        "from": doctor,   # msg.sender
        "nonce": w3.eth.get_transaction_count(doctor),
        "gas": 5_000_000,
        "chainId": w3.eth.chain_id,
    })

    # Debug
    try:
        w3.eth.call(tx)
        print("CALL SUCCESS ✅ (no revert)")
    except Exception as e:
        print("REVERT →", e)

    return tx


def resolve_patient(name: str):
    contract = _load_contract()
    print(name)

    patient_address = contract.functions.getAddressByName(name).call()
    print(patient_address)

    if int(patient_address, 16) == 0:
        return None, None, None, None

    patient = Web3.to_checksum_address(patient_address)
    print(patient)

    idHash, pubKey, exists, name = contract.functions.identities(patient).call()

    record_id = contract.functions.getRecordIdByOwner(patient).call()
    record_id_hex = Web3.to_hex(record_id)

    return (
        patient_address,
        record_id_hex,
        Web3.to_hex(idHash),
        str(int.from_bytes(idHash, "big"))
    )

from web3 import Web3

def _topic0_for(event_signature: str) -> str:
    # e.g. "AccessRequested(address,address,bytes32,bytes32,uint64)"
    res = Web3.keccak(text=event_signature).hex()
    if res.startswith("0x"):
        return res
    return "0x" + res

def _topic_for_address(addr: str) -> str:
    # topic needs 32-byte left-padded value
    res= Web3.to_hex(Web3.to_bytes(hexstr=Web3.to_checksum_address(addr)).rjust(32, b"\x00"))
    if res.startswith("0x"):
        return res
    return "0x" + res

def _get_name_of(wallet: str) -> str:
    """
    Look up name associated with wallet address.
    identities(addr) returns (idHash, pubKey, exists, name)
    """
    registry = _load_contract()
    wallet = Web3.to_checksum_address(wallet)

    idHash, pubKey, exists, name = registry.functions.identities(wallet).call()
    if exists:
        return name
    return ""

def fetch_access_logs_for_doctor(doctor: str):
    registry = _load_contract()
    doctor = Web3.to_checksum_address(doctor)

    # topic[0] = keccak(event signature)
    topic0 = _topic0_for("AccessRequested(address,address,bytes32,bytes32,uint64)")
    topic1 = _topic_for_address(doctor)   # indexed provider

    logs = w3.eth.get_logs({
        "address": registry.address,
        "fromBlock": 0,
        "toBlock": "latest",
        "topics": [topic0, topic1, None, None],  
        #           sig   provider  patient   recordId
    })

    events = []
    for log in logs:
        ev = registry.events.AccessRequested().process_log(log)
        provider = ev["args"]["provider"]
        patient  = ev["args"]["patient"]
        events.append({
            "doctor_address": provider,
            "doctor_name": _get_name_of(provider),
            "patient_address": patient,
            "patient_name": _get_name_of(patient),
            "record_id": ev["args"]["recordId"].hex(),
            "token": ev["args"]["token"].hex(),
            "expiresAt": int(ev["args"]["expiresAt"]),
        })
    return events

def fetch_access_logs_for_patient(patient: str):
    registry = _load_contract()
    patient = Web3.to_checksum_address(patient)

    topic0 = _topic0_for("AccessRequested(address,address,bytes32,bytes32,uint64)")
    topic2 = _topic_for_address(patient)   # indexed patient

    logs = w3.eth.get_logs({
        "address": registry.address,
        "fromBlock": 0,
        "toBlock": "latest",
        "topics": [topic0, None, topic2, None],
        #           sig   provider patient recordId
    })

    events = []
    for log in logs:
        ev = registry.events.AccessRequested().process_log(log)

        provider = ev["args"]["provider"]
        patient_ = ev["args"]["patient"]

        events.append({
            "doctor_address": provider,
            "doctor_name": _get_name_of(provider),
            "patient_address": patient_,
            "patient_name": _get_name_of(patient_),
            "record_id": ev["args"]["recordId"].hex(),
            "token": ev["args"]["token"].hex(),
            "expiresAt": int(ev["args"]["expiresAt"]),
        })

    return events

def get_record_by_id(record_id: str):
    contract = _load_contract()
    rid = _b32(record_id)
    print(rid)
    owner, h, encryptedCid, consent, timestamp = contract.functions.getRecord(rid).call()

    return {
        "owner": owner,
        "h": h.hex() if isinstance(h, bytes) else h,
        "encryptedCid": encryptedCid,
        "consent": consent,
        "timestamp": timestamp,
    }

def check_token_valid(token: str):
    contract = _load_contract()
    t = _b32(token)
    return contract.functions.tokenValid(t).call()

def toggle_consent_tx(eth_address, record_id, active):
    contract = _load_contract()
    eth_address = Web3.to_checksum_address(eth_address)

    rid = _b32(record_id)
    print(rid)

    owner, _, _, _, _ = contract.functions.getRecord(rid).call()
    print("Owner = ", owner)


    tx = contract.functions.toggleConsent(
        rid,
        bool(active)
    ).build_transaction({
        "from": eth_address,
        "nonce": w3.eth.get_transaction_count(eth_address),
        "gas": 300000,
        "chainId": w3.eth.chain_id,
    })

    try:
        w3.eth.call(tx)
        print("CALL OK ✅ toggleConsent")
    except Exception as e:
        print("REVERT →", e)

    return tx
