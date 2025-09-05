require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: "0.8.20",
  networks: {
    ganache: {
      url: "http://127.0.0.1:7545",
      accounts: ["0x3f73188e049412413eb5198114d1818562b23e00e1363877cea73ad531d1a030"]
    }
  }
};
