require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      },
      viaIR: true
    }
  },
  networks: {
    ganache: {
      url: "http://127.0.0.1:7545",
      accounts: ["0x847cbebb3bdcbe38eb7b65bc3e28d1ff868e690b80f9cd4c318f857673ecafff"]
    }
  }
};
