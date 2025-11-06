function toHex(v) {
  if (v === undefined || v === null) return undefined;

  if (typeof v === "string") {
    if (v.startsWith("0x")) return v;     // already hex
    if (!isNaN(v)) return "0x" + window.BigInt(v).toString(16);
  }

  try {
    return "0x" + window.BigInt(v).toString(16);
  } catch (e) {
    console.warn("Bad toHex:", v);
    return undefined;
  }
}

function normalizeTx(tx) {
  const out = { ...tx };

  // ✅ Remove conflicting EIP-1559 fields
  delete out.gasPrice;
  delete out.maxFeePerGas;
  delete out.maxPriorityFeePerGas;

  // ✅ Required hex fields
  out.chainId = toHex(out.chainId);
  out.gas     = toHex(out.gas);
  out.value   = toHex(out.value ?? 0);
  out.nonce   = toHex(out.nonce);

  // ✅ Ensure "to" is present
  if (!out.to) {
    console.error("❌ tx.to missing");
  }

  return out;
}


export async function sendTx(txData) {
    txData = normalizeTx(txData);
    console.log(txData);
  return await window.ethereum.request({
    method: "eth_sendTransaction",
    params: [txData]
  });
}
