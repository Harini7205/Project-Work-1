require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: "0.8.20",
  networks: {
    ganache: {
      url: "http://127.0.0.1:7545",
      accounts: ["0xed4c5f73a29512aee0e25479b5ca5415b46a6295759268071e08889dfa1ea15e"]
    }
  }
};
