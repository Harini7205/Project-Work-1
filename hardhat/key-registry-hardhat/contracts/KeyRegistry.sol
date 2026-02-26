// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract AccessRegistry {

    // ----------------------------------------------------------
    // STRUCTS
    // ----------------------------------------------------------

    struct Identity {
        bytes32 idHash;
        bytes   pubKey;
        bool    exists;
    }

    struct Record {
        address owner;
        bytes32 h;
        string  encryptedCid;
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
    mapping(bytes32 => Record) public records;
    mapping(address => bytes32[]) public patientRecords;
    mapping(bytes32 => string[]) public recordHistory;

    mapping(bytes32 => bool) public usedRequest;
    mapping(bytes32 => uint64) public tokenExpiry;
    mapping(address => Rate) public rate;

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
    // 1) REGISTER IDENTITY
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
    // AUTO REGISTER IDENTITY IF MISSING
    // ----------------------------------------------------------

    function autoRegister() internal {
        if (!identities[msg.sender].exists) {
            identities[msg.sender] = Identity({
                idHash: keccak256(abi.encodePacked(msg.sender)),
                pubKey: "",
                exists: true
            });

            emit IdentityRegistered(msg.sender, keccak256(abi.encodePacked(msg.sender)));
        }
    }

    // ----------------------------------------------------------
    // 2) STORE RECORD (FIXED)
    // ----------------------------------------------------------

    function storeRecord(
        bytes32 recordId,
        bytes32 h,
        string calldata encryptedCid,
        bool consentActive
    ) external {

        // AUTO REGISTER
        autoRegister();

        require(records[recordId].timestamp == 0, "Record exists");

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
    // 3) UPDATE RECORD
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
    // 5) ACCESS REQUEST
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

        require(identities[patient].exists, "Patient not registered");

        Record memory rec = records[recordId];
        require(rec.owner == patient, "Owner mismatch");
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

    function getRecordIdByOwner(address patient)
        external
        view
        returns (bytes32)
    {
        bytes32[] memory lst = patientRecords[patient];
        return lst.length == 0 ? bytes32(0) : lst[lst.length - 1];
    }

    function tokenValid(bytes32 token)
        external
        view
        returns (bool)
    {
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

    function isRegistered(address user)
        external
        view
        returns (bool)
    {
        return identities[user].exists;
    }
}
