import { useState } from "react";
import { API } from "../api/api";
import "../styling/admin.css";
import { sendTx } from "./TransactionUtils";

export default function Admin() {

  const wallet = localStorage.getItem("wallet");
  const pub = localStorage.getItem("pub");

  const [file, setFile] = useState(null);
  const [encBlob, setEncBlob] = useState(null);
  const [cid, setCid] = useState("");
  const [ch, setCh] = useState("");
  const [rHex, setRHex] = useState("");
  const [recordId, setRecordId] = useState("");

  const [encrypting, setEncrypting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [hashing, setHashing] = useState(false);
  const [storing, setStoring] = useState(false);

  // STEP 1 - Encrypt
  const doEncrypt = async () => {
    if (!file || !pub) return alert("Missing file or public key");

    setEncrypting(true);
    try {
      const form = new FormData();
      form.append("file", file);

      const res = await API.post("/encrypt", form, {
        responseType: "blob",
      });

      const blob = new Blob([res.data]);
      setEncBlob(blob);

      alert("Encrypted successfully");
    } catch {
      alert("Encryption failed");
    }
    setEncrypting(false);
  };

  // STEP 2 - Upload
  const doUpload = async () => {
    if (!encBlob) return alert("Encrypt first");

    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", encBlob);

      const res = await API.post("/ipfs-upload", form);
      setCid(res.data.cid);

      alert("Uploaded to IPFS");
    } catch {
      alert("Upload failed");
    }
    setUploading(false);
  };

  // STEP 3 - Hash
  const doHash = async () => {
    if (!cid) return alert("Upload first");

    setHashing(true);
    try {
      const form = new FormData();
      form.append("public_key_hex", pub);

      const res = await API.post(`/chameleon-hash/${cid}`, form);

      setCh(res.data.ch);
      setRHex(res.data.r);

      alert("Hash generated");
    } catch {
      alert("Hash failed");
    }
    setHashing(false);
  };

  // STEP 4 - Store
  const doStore = async () => {
    if (!cid || !ch || !wallet) return alert("Missing data");

    setStoring(true);
    try {
      const form = new FormData();
      form.append("cid", cid);
      form.append("ch", ch);
      form.append("eth_address", wallet);

      const res = await API.post("/store-record", form);

      setRecordId(res.data.record_id);

      const txHash = await sendTx(res.data.tx_data);

      alert("Stored on blockchain\nTx: " + txHash);

    } catch {
      alert("Store failed");
    }
    setStoring(false);
  };

  return (
    <div className="admin-wrapper">

      <h1>Admin Dashboard</h1>

      <div className="admin-card">

        <h3>Step 1: Choose File</h3>
        <input type="file" onChange={(e)=>setFile(e.target.files[0])} />

        <h3>Step 2: Encrypt</h3>
        <button onClick={doEncrypt}>
          Encrypt File
        </button>

        <h3>Step 3: Upload</h3>
        <button onClick={doUpload}>
          Upload to IPFS
        </button>

        <h3>Step 4: Hash</h3>
        <button onClick={doHash}>
          Generate Hash
        </button>

        <h3>Step 5: Store</h3>
        <button onClick={doStore}>
          Store on Chain
        </button>

        <hr />

        <p><b>CID:</b> {cid}</p>
        <p><b>Hash:</b> {ch}</p>
        <p><b>Record ID:</b> {recordId}</p>

      </div>

    </div>
  );
}