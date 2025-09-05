// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract KeyRegistry {
    struct Record {
        address owner;
        bytes pubKey;
        bytes32 h;
        string encryptedCid;
        uint256 timestamp;
        bool exists;
    }

    mapping(address => Record) private records;

    // Register public key
    function registerKey(bytes calldata pubKey) external {
        require(!records[msg.sender].exists, "Already registered");
        records[msg.sender] = Record({
            owner: msg.sender,
            pubKey: pubKey,
            h: bytes32(0),
            encryptedCid: "",
            timestamp: block.timestamp,
            exists: true
        });
    }

    // Store hash and encrypted CID
    function storeData(bytes32 h, string calldata encryptedCid) external {
        require(records[msg.sender].exists, "Key not registered");
        records[msg.sender].h = h;
        records[msg.sender].encryptedCid = encryptedCid;
        records[msg.sender].timestamp = block.timestamp;
    }

    // Retrieve record
    function getRecord(address owner) external view returns (bytes memory, bytes32, string memory, uint256, bool) {
        Record storage r = records[owner];
        return (r.pubKey, r.h, r.encryptedCid, r.timestamp, r.exists);
    }

    // Verify hash
    function verifyHash(bytes32 hCandidate) external view returns (bool) {
        require(records[msg.sender].exists, "Key not registered");
        return records[msg.sender].h == hCandidate;
    }
}
