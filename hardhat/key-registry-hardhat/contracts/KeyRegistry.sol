// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract AccessRegistry {

    // ----------------------------------------------------------
    // STRUCTS
    // ----------------------------------------------------------

    struct Identity {
        bytes32 idHash;   // keccak256(pubKey)
        bytes   pubKey;   // ECC public key bytes
        bool    exists;
    }

    struct Record {
        address owner;        // patient wallet
        bytes32 h;            // chameleon hash
        string  encryptedCid; // IPFS CID
        bool    consentActive;
        uint256 timestamp;
    }

    struct Rate {
        uint32 count;
        uint64 windowStart;
    }

    // ----------------------------------------------------------
    // STORAGE
    // ----------------------------------------------------------

    bytes32 public DOMAIN_SEPARATOR;

    mapping(address => Identity) public identities;
    mapping(bytes32 => Record)   public records;
    mapping(address => bytes32[]) public patientRecords;
    mapping(bytes32 => string[]) public recordHistory;

    mapping(bytes32 => bool)   public usedRequest;
    mapping(bytes32 => uint64) public tokenExpiry;
    mapping(address => Rate)   public rate;

    // ----------------------------------------------------------
    // EVENTS
    // ----------------------------------------------------------

    event IdentityRegistered(address indexed user, bytes32 idHash);
    event RecordStored(bytes32 indexed recordId, address indexed owner);
    event RecordUpdated(bytes32 indexed recordId, string newCid);
    event ConsentToggled(address indexed patient, bytes32 indexed recordId, bool active);
    event AccessRequested(
        address indexed provider,
        address indexed patient,
        bytes32 indexed recordId,
        bytes32 token,
        uint64 expiresAt
    );

    // ----------------------------------------------------------
    // CONSTANTS
    // ----------------------------------------------------------

    bytes32 public constant EIP712_DOMAIN_TYPEHASH =
        keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");

    bytes32 public constant REQUEST_TYPEHASH =
        keccak256(
            "AccessRequest(address provider,address patient,bytes32 recordId,uint8 role,uint64 timestamp,uint256 nonce)"
        );

    uint8 public constant ROLE_DOCTOR = 0;

    // ----------------------------------------------------------
    // CONSTRUCTOR
    // ----------------------------------------------------------

    constructor() {
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                EIP712_DOMAIN_TYPEHASH,
                keccak256(bytes("AccessRegistry")),
                keccak256(bytes("1")),
                block.chainid,
                address(this)
            )
        );
    }

    // ----------------------------------------------------------
    // 1) REGISTER IDENTITY (ONCE PER WALLET)
    // ----------------------------------------------------------

    function registerIdentity(bytes calldata pubKey) external {
        require(!identities[msg.sender].exists, "Already registered");

        bytes32 idHash = keccak256(pubKey);

        identities[msg.sender] = Identity({
            idHash: idHash,
            pubKey: pubKey,
            exists: true
        });

        emit IdentityRegistered(msg.sender, idHash);
    }

    // ----------------------------------------------------------
    // 2) STORE MEDICAL RECORD
    // ----------------------------------------------------------

    function storeRecord(
        bytes32 recordId,
        bytes32 h,
        string calldata encryptedCid,
        bool consentActive
    ) external {
        require(identities[msg.sender].exists, "Identity missing");
        require(records[recordId].timestamp == 0, "Record already exists");

        records[recordId] = Record({
            owner: msg.sender,
            h: h,
            encryptedCid: encryptedCid,
            consentActive: consentActive,
            timestamp: block.timestamp
        });

        patientRecords[msg.sender].push(recordId);

        emit RecordStored(recordId, msg.sender);
    }

    // ----------------------------------------------------------
    // 3) UPDATE RECORD (REDACTION)
    // ----------------------------------------------------------

    function updateRecord(
        bytes32 recordId,
        bytes32 newH,
        string calldata newCid
    ) external {
        Record storage r = records[recordId];
        require(r.owner == msg.sender, "Unauthorized");

        recordHistory[recordId].push(r.encryptedCid);

        r.h = newH;
        r.encryptedCid = newCid;
        r.timestamp = block.timestamp;

        emit RecordUpdated(recordId, newCid);
    }

    // ----------------------------------------------------------
    // 4) TOGGLE CONSENT
    // ----------------------------------------------------------

    function toggleConsent(bytes32 recordId, bool active) external {
        Record storage r = records[recordId];
        require(r.owner == msg.sender, "Unauthorized");

        r.consentActive = active;

        emit ConsentToggled(msg.sender, recordId, active);
    }

    // ----------------------------------------------------------
    // 5) ACCESS REQUEST (EIP-712)
    // ----------------------------------------------------------

    function requestAccess(
        address patient,
        bytes32 recordId,
        uint8 role,
        uint64 timestamp,
        uint256 nonce,
        uint8 v, bytes32 r, bytes32 s,
        uint64 ttlSeconds
    ) external returns (bytes32 token, uint64 expiresAt) {

        Rate storage rl = rate[msg.sender];
        if (block.timestamp - rl.windowStart > 3600) {
            rl.windowStart = uint64(block.timestamp);
            rl.count = 0;
        }
        require(rl.count < 10, "Rate limited");
        rl.count++;

        bytes32 reqHash = keccak256(
            abi.encode(
                REQUEST_TYPEHASH,
                msg.sender,
                patient,
                recordId,
                role,
                timestamp,
                nonce
            )
        );

        bytes32 digest = keccak256(
            abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, reqHash)
        );

        require(ecrecover(digest, v, r, s) == msg.sender, "Bad signature");
        require(!usedRequest[reqHash], "Replay");
        require(role == ROLE_DOCTOR, "Only doctor allowed");

        usedRequest[reqHash] = true;

        require(identities[patient].exists, "Patient not registered");

        Record memory rec = records[recordId];
        require(rec.owner == patient, "Record owner mismatch");
        require(rec.consentActive, "Consent inactive");

        token = keccak256(
            abi.encode(patient, msg.sender, recordId, block.timestamp, nonce)
        );
        expiresAt = uint64(block.timestamp + ttlSeconds);
        tokenExpiry[token] = expiresAt;

        emit AccessRequested(msg.sender, patient, recordId, token, expiresAt);
    }

    // ----------------------------------------------------------
    // VIEW HELPERS
    // ----------------------------------------------------------

    function getRecordIdByOwner(address patient) external view returns (bytes32) {
        bytes32[] memory lst = patientRecords[patient];
        return lst.length == 0 ? bytes32(0) : lst[lst.length - 1];
    }

    function tokenValid(bytes32 token) external view returns (bool) {
        return tokenExpiry[token] >= block.timestamp;
    }

    function getRecord(bytes32 recordId)
        external
        view
        returns (
            address owner,
            bytes32 h,
            string memory encryptedCid,
            bool consentActive,
            uint256 timestamp
        )
    {
        Record memory r = records[recordId];
        return (r.owner, r.h, r.encryptedCid, r.consentActive, r.timestamp);
    }

    // ----------------------------------------------------------
    // VIEW: CHECK IF IDENTITY IS REGISTERED
    // ----------------------------------------------------------
    function isRegistered(address user) external view returns (bool) {
        return identities[user].exists;
    }
}

