// src/pages/Patient.jsx
import { useState, useEffect } from "react";
import { API } from "../api/api";
import "../styling/patient.css";
import {
  FaBell,
  FaUserCircle,
  FaCloudUploadAlt
} from "react-icons/fa";
import { sendTx } from "../pages/TransactionUtils";

export default function Patient() {
  const patientName = localStorage.getItem("name");
  const wallet = localStorage.getItem("wallet");
  const pub = localStorage.getItem("pub");

  /* ---------------- UI STATE ---------------- */
  const [file, setFile] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [showRequests, setShowRequests] = useState(false);
  const [requests, setRequests] = useState([]);
  const [consentActive, setConsentActive] = useState(true);

  /* ---------------- PROCESS STATE ---------------- */
  const [encrypting, setEncrypting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [hashing, setHashing] = useState(false);
  const [storing, setStoring] = useState(false);
  const [isRedaction, setIsRedaction] = useState(false);

  /* ---------------- DATA ---------------- */
  const [encBlob, setEncBlob] = useState(null);
  const [cid, setCid] = useState(localStorage.getItem("last_cid") || "");
  const [ch, setCh] = useState(localStorage.getItem("ch") || "");
  const [rHex, setRHex] = useState(localStorage.getItem("last_r") || "");
  const [recordId, setRecordId] = useState(localStorage.getItem("record_id") || "");

  const short = (x = "") =>
    x.length > 12 ? x.slice(0, 6) + "..." + x.slice(-4) : x;

  /* ======================================================
     ACCESS REQUESTS (READ-ONLY, ON-CHAIN)
  ====================================================== */
  const fetchRequests = async () => {
    try {
      const res = await API.get(`/requests/patient?email=${localStorage.getItem("email")}`);
      setRequests(res.data.requests || []);
    } catch {
      setRequests([]);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  /* ======================================================
     STEP 1 — ENCRYPT
  ====================================================== */
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

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "encrypted_ehr.enc";
      a.click();

      alert("✅ Encrypted successfully");
    } catch {
      alert("❌ Encryption failed");
    } finally {
      setEncrypting(false);
    }
  };

  /* ======================================================
     STEP 2 — UPLOAD IPFS
  ====================================================== */
  const doUploadToIPFS = async () => {
    if (!encBlob) return alert("Encrypt first");

    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", encBlob);

      const res = await API.post("/ipfs-upload", form);
      setCid(res.data.cid);
      localStorage.setItem("last_cid", res.data.cid);

      alert("✅ Uploaded to IPFS");
    } catch {
      alert("❌ IPFS upload failed");
    } finally {
      setUploading(false);
    }
  };

  /* ======================================================
     STEP 3 — CHAMELEON HASH
  ====================================================== */
  const doChameleonHash = async () => {
    if (!cid) return alert("Upload to IPFS first");

    setHashing(true);
    try {
      const form = new FormData();
      form.append("public_key_hex", pub);

      const res = await API.post(`/chameleon-hash/${cid}`, form);
      setCh(res.data.ch);
      setRHex(res.data.r);

      localStorage.setItem("ch", res.data.ch);
      localStorage.setItem("last_r", res.data.r);

      alert("✅ Hash generated");
    } catch {
      alert("❌ Hash failed");
    } finally {
      setHashing(false);
    }
  };

  /* ======================================================
     STEP 4 — STORE / REDACT
  ====================================================== */
  const doStoreOnChain = async () => {
    if (!wallet || !cid || !ch) return;

    setStoring(true);
    try {
      let res;
      if (isRedaction) {
        const form = new FormData();
        form.append("file", encBlob);
        form.append("old_cid", localStorage.getItem("last_cid"));
        form.append("old_r_hex", localStorage.getItem("last_r"));
        form.append("c_hash", localStorage.getItem("ch"));
        form.append("public_key_hex", pub);
        form.append("private_key_hex", localStorage.getItem("priv"));
        form.append("record_id", recordId);
        form.append("eth_address", wallet);
        form.append("consent_active", "true");

        res = await API.post("/redact", form);
      } else {
        const form = new FormData();
        form.append("cid", cid);
        form.append("ch", ch);
        form.append("eth_address", wallet);

        res = await API.post("/store-record", form);
        setRecordId(res.data.record_id);
        localStorage.setItem("record_id", res.data.record_id);
      }

      const txHash = await sendTx(res.data.tx_data);
      alert(`✅ Stored on-chain\nTx: ${txHash}`);
      setIsRedaction(false);
    } catch {
      alert("❌ Blockchain store failed");
    } finally {
      setStoring(false);
    }
  };

  /* ======================================================
     CONSENT TOGGLE
  ====================================================== */
  const toggleConsent = async () => {
    if (!recordId) return;

    try {
      const form = new FormData();
      form.append("record_id", recordId);
      form.append("eth_address", wallet);
      form.append("active", !consentActive);

      const res = await API.post("/toggle-consent", form);
      await sendTx(res.data.tx_data);

      setConsentActive(!consentActive);
    } catch {
      alert("❌ Consent toggle failed");
    }
  };

  /* ======================================================
     VIEW EHR
  ====================================================== */
  const viewEHR = async () => {
   try {
      if (!cid) return alert("No CID stored");

      const res = await API.get(`/download/${cid}`, { responseType: "blob" });
      console.log(res);
      const blob = res.data;

    // ✅ Auto-download
    const file = new Blob([blob], { type: "application/pdf" });

    // create temporary object URL
    const fileURL = URL.createObjectURL(file);

    // automatically trigger browser download
    window.open(fileURL);

    // optional: revoke url later
    setTimeout(() => URL.revokeObjectURL(fileURL), 5000);

    } catch {
      alert("❌ Download failed");
    }
  };

  /* ======================================================
     STEP LOGIC
  ====================================================== */
  const step =
    recordId ? "done" :
    !encBlob ? "encrypt" :
    !cid ? "upload" :
    !ch ? "hash" :
    "store";

  const handleStep = () => {
    if (step === "encrypt") return doEncrypt();
    if (step === "upload") return doUploadToIPFS();
    if (step === "hash") return doChameleonHash();
    if (step === "store") return doStoreOnChain();
  };

  /* ======================================================
     RENDER
  ====================================================== */
  return (
    <div className="patient-wrapper">
      <header className="patient-header">
        <h2>EHRChain</h2>

        <div className="bell" onClick={() => setShowRequests(!showRequests)}>
          <FaBell />
          {requests.length > 0 && <span className="badge">{requests.length}</span>}
        </div>

        <div className="user-info" onClick={() => setShowDropdown(!showDropdown)}>
          <FaUserCircle />
          <span>{patientName}</span>
        </div>
      </header>

      {showRequests && (
        <div className="requests-popup">
          <h3>Access Logs</h3>
          {requests.map((r, i) => (
            <div key={i} className="request-item-card">
              <p>Doctor: {r.doctor}</p>
              <p>Status: {r.status}</p>
              <p>Token: {short(r.token)}</p>
            </div>
          ))}
        </div>
      )}

      <div className="patient-main">
        <h1>Welcome, {patientName}</h1>

        <div className="upload-card">
          <FaCloudUploadAlt />
          {step === "encrypt" && <input type="file" onChange={(e) => setFile(e.target.files[0])} />}

          {step !== "done" && (
            <button className="upload-btn" onClick={handleStep}>
              {step.toUpperCase()}
            </button>
          )}

          {step === "done" && (
            <>
              <button className="upload-btn" onClick={viewEHR}>View EHR</button>
              <button className="upload-btn" onClick={() => setIsRedaction(true)}>Redact</button>
              <button
                className="upload-btn"
                style={{ background: consentActive ? "#f33" : "#3c3" }}
                onClick={toggleConsent}
              >
                {consentActive ? "Disable Consent" : "Enable Consent"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
