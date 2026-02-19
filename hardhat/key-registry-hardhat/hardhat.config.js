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
      accounts: ["0x65ecb124e4ff06b4582098b50f6ab13c1f89ff324be619c7df100e3906f84a86"]
    }
  }
};
