const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const [deployer] = await hre.ethers.getSigners();

  // Read deployed contract address
  const filePath = path.join(__dirname, "deployedAddress.json");
  if (!fs.existsSync(filePath)) {
    console.error("deployedAddress.json not found! Run deploy.js first.");
    process.exit(1);
  }
  const data = JSON.parse(fs.readFileSync(filePath));
  const contractAddr = data.address;

  const KeyRegistry = await hre.ethers.getContractFactory("KeyRegistry");
  const registry = await KeyRegistry.attach(contractAddr);

  // 1️⃣ Register key (dummy public key)
  const tx1 = await registry.registerKey("0x1234");
  await tx1.wait();
  console.log("Key registered");

  // 2️⃣ Store hash and encrypted CID (dummy values) with higher gas limit
  const h = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
  const cid = "bafybeigdummyEncryptedCID12345";
  const tx2 = await registry.storeData(h, cid, { gasLimit: 500_000 });
  await tx2.wait();
  console.log("Data stored");

  // 3️⃣ Verify hash
  const result = await registry.verifyHash(h);
  console.log("Verification result:", result);

  // 4️⃣ Fetch record
  const record = await registry.getRecord(deployer.address);
  console.log("Record:", record);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
