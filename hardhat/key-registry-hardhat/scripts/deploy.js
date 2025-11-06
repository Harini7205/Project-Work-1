const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const AccessRegistry = await hre.ethers.getContractFactory("AccessRegistry");
  // In ethers v6, deploy() returns the deployed contract directly
  const registry = await AccessRegistry.deploy(); 

  console.log("AccessRegistry deployed to:", registry.target); // .target replaces .address in v6

  // Save deployed address to a file
  const data = {
    registry: registry.target
  };
  const filePath = path.join(__dirname, "deployedAddress.json");
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
  console.log("Contract address saved to deployedAddress.json");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
