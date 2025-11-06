// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract AccessRegistry {
    // ----------------------------------------------------------
    // STRUCTS
    // ----------------------------------------------------------

    struct Identity {
        bytes32 idHash;   // keccak256(pubKey)
        bytes   pubKey;   // arbitrary user pubkey bytes
        bool    exists;
        string  name;
    }

    struct Record {
        address owner;        // patient wallet
        bytes32 h;            // chameleon hash
        string  encryptedCid; // IPFS CID (encrypted file)
        bool    consentActive;
        uint256 timestamp;    // last updated
    }

    // ----------------------------------------------------------
    // STORAGE
    // ----------------------------------------------------------

    bytes32 public DOMAIN_SEPARATOR;

    // Identities
    mapping(address => Identity) public identities;     // wallet → identity
    mapping(string  => address) public nameToAddress;   // name → wallet

    // Medical records
    mapping(bytes32 => Record)    public records;        // recordId → record
    mapping(address => bytes32[]) public patientRecords; // patient → list of recordIds

    // Redaction history
    mapping(bytes32 => string[]) public recordHistory;   // recordId → older CIDs

    // Replay + token
    mapping(bytes32 => bool)   public usedRequest; // EIP-712 request hash used
    mapping(bytes32 => uint64) public tokenExpiry; // token → expiry

    // Rate limiting per provider
    struct Rate { uint32 count; uint64 windowStart; }
    mapping(address => Rate) public rate;

    // ----------------------------------------------------------
    // EVENTS
    // ----------------------------------------------------------

    event IdentityRegistered(address indexed user, string name, bytes32 idHash);
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

    // Keep the same typed data as before (role kept for forward compatibility)
    bytes32 public constant REQUEST_TYPEHASH =
        keccak256("AccessRequest(address provider,address patient,bytes32 recordId,uint8 role,uint64 timestamp,uint256 nonce)");

    // role = 0 => doctor (kept for compatibility)
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
    // 1) REGISTER IDENTITY
    // ----------------------------------------------------------

    function registerIdentity(bytes calldata pubKey, string calldata name) external {
        require(bytes(name).length > 0, "Name required");

        bytes32 idHash = keccak256(pubKey);

        identities[msg.sender] = Identity(idHash, pubKey, true, name);
        nameToAddress[name] = msg.sender;

        emit IdentityRegistered(msg.sender, name, idHash);
    }

    // ----------------------------------------------------------
    // 2) STORE ENCRYPTED MEDICAL RECORD
    // ----------------------------------------------------------

    function storeRecord(
        bytes32 recordId,
        bytes32 h,
        string calldata encryptedCid,
        bool consentActive
    ) external {
        require(identities[msg.sender].exists, "Identity missing");

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

        // push old CID to history
        recordHistory[recordId].push(r.encryptedCid);

        r.h = newH;
        r.encryptedCid = newCid;
        r.timestamp = block.timestamp;

        emit RecordUpdated(recordId, newCid);
    }

    // ----------------------------------------------------------
    // 4) CONSENT Toggle
    // ----------------------------------------------------------

    function toggleConsent(bytes32 recordId, bool active) external {
        Record storage r = records[recordId];
        require(r.owner == msg.sender, "Unauthorized");
        r.consentActive = active;
        emit ConsentToggled(msg.sender, recordId, active);
    }

    // ----------------------------------------------------------
    // 5) ACCESS REQUEST (No ZKP) — EIP-712 signed by doctor
    // ----------------------------------------------------------
    /**
     * The doctor (msg.sender) signs the EIP-712 request off-chain.
     * We verify the sig belongs to msg.sender, ensure consent is active,
     * protect against replay, then mint a time-limited token.
     */
    function requestAccess(
        address patient,
        bytes32 recordId,
        uint8 role,          // must be ROLE_DOCTOR (0)
        uint64 timestamp,    // client timestamp (optional semantics)
        uint256 nonce,       // unique per request to prevent replay
        uint8 v, bytes32 r, bytes32 s,
        uint64 ttlSeconds
    ) external returns (bytes32 token, uint64 expiresAt)
    {
        // Simple per-hour rate limiting for provider (doctor)
        Rate storage rl = rate[msg.sender];
        if (block.timestamp - rl.windowStart > 3600) {
            rl.windowStart = uint64(block.timestamp);
            rl.count = 0;
        }
        require(rl.count < 10, "Rate limited");
        rl.count++;

        // Build typed data hash
        bytes32 reqHash = keccak256(
            abi.encode(
                REQUEST_TYPEHASH,
                msg.sender,   // provider
                patient,
                recordId,
                role,
                timestamp,
                nonce
            )
        );
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, reqHash));

        // Signature must be from the calling doctor
        address signer = ecrecover(digest, v, r, s);
        require(signer == msg.sender, "Bad signature");

        // Replay protection
        require(!usedRequest[reqHash], "Replay");
        usedRequest[reqHash] = true;

        // Role check (optional — keep parity with your frontend)
        require(role == ROLE_DOCTOR, "Only doctor allowed");

        // Patient identity must exist
        Identity memory id = identities[patient];
        require(id.exists, "No identity");

        // Record must exist and belong to patient
        Record memory rec = records[recordId];
        require(rec.owner == patient, "Record owner mismatch");

        // Consent must be active
        require(rec.consentActive, "Consent inactive");

        // Optional: ensure client timestamp isn't absurdly old/new (anti-replay window)
        // e.g., require(block.timestamp + 5 minutes >= timestamp && timestamp + 15 minutes >= block.timestamp, "Stale/future ts");

        // Mint time-limited token bound to (patient, provider, recordId)
        token = keccak256(abi.encode(patient, msg.sender, recordId, block.timestamp, nonce));
        expiresAt = uint64(block.timestamp + ttlSeconds);
        tokenExpiry[token] = expiresAt;

        emit AccessRequested(msg.sender, patient, recordId, token, expiresAt);
    }

    // ----------------------------------------------------------
    // ✅ VIEW HELPERS
    // ----------------------------------------------------------

    function getAddressByName(string memory name) external view returns (address) {
        return nameToAddress[name];
    }

    function getRecordIdByOwner(address patient) external view returns (bytes32) {
        bytes32[] memory lst = patientRecords[patient];
        if (lst.length == 0) return bytes32(0);
        return lst[lst.length - 1];
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

    function getRecordsOf(address patient) external view returns (bytes32[] memory) {
        return patientRecords[patient];
    }

    // EIP-712 pieces for debugging
    function getDomainSeparator() external view returns (bytes32) {
        return DOMAIN_SEPARATOR;
    }

    function typeHashAccessRequest() public pure returns (bytes32) {
        return keccak256(
            bytes(
                "AccessRequest(address provider,address patient,bytes32 recordId,uint8 role,uint64 timestamp,uint256 nonce)"
            )
        );
    }

    function debugReqHash(
        address provider,
        address patient,
        bytes32 recordId,
        uint8 role,
        uint64 timestamp,
        uint256 nonce
    ) external view returns (bytes32 reqHash, bytes32 digest) {
        bytes32 th = typeHashAccessRequest();
        reqHash = keccak256(abi.encode(th, provider, patient, recordId, role, timestamp, nonce));
        digest  = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, reqHash));
    }
}
