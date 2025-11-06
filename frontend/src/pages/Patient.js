import { useState, useEffect } from "react";
import { API } from "../api/api";
import "../styling/patient.css";
import { FaBell, FaUserCircle, FaCloudUploadAlt, FaCheck, FaTimes } from "react-icons/fa";
import { sendTx } from "../pages/TransactionUtils";

export default function Patient() {
  const patientName = localStorage.getItem("name");

  // UI state
  const [file, setFile] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [showRequests, setShowRequests] = useState(false);
  const [requests, setRequests] = useState([]);
  const [consentActive, setConsentActive] = useState(true);

  // Step booleans
  const [encrypting, setEncrypting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [hashing, setHashing] = useState(false);
  const [storing, setStoring] = useState(false);

  // runtime
  const [encBlob, setEncBlob] = useState(null);
  const [isRedaction, setIsRedaction] = useState(false);   // <—— NEW

  // Last saved details
  const [cid, setCid]       = useState(localStorage.getItem("last_cid") || "");
  const [ch, setCh]         = useState(localStorage.getItem("ch") || "");
  const [rHex, setRHex]     = useState(localStorage.getItem("last_r") || "");
  const [recordId, setRecordId] = useState(localStorage.getItem("record_id") || "");
  const [txHash, setTxHash] = useState("");

  const pub    = localStorage.getItem("pub");
  const wallet = localStorage.getItem("wallet");

  const short = (a = "") => (a?.length > 12 ? a.slice(0,6) + "..." + a.slice(-4) : a);

  /* --------------------------
        ACCESS REQUESTS
  ---------------------------*/
  const fetchRequests = async () => {
    try {
      const res = await API.get(`/requests?patient_name=${patientName}`);
      setRequests(res.data.requests || []);
    } catch {}
  };
  useEffect(() => {
    fetchRequests();
  }, []);

  /* =========================
     STEP 1 — ENCRYPT
  ========================= */
  const doEncrypt = async () => {
    if (!file) return alert("Select a file first.");
    if (!pub)  return alert("Missing public key");

    setEncrypting(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("public_key_hex", pub);
      form.append("consent_active", true);

      const res = await API.post("/encrypt", form, { responseType: "blob" });
      const blob = new Blob([res.data]);
      setEncBlob(blob);

      localStorage.setItem("enc_ready", "1");
      localStorage.setItem("enc_size", blob.size);

      alert("✅ Encrypted. Now upload to IPFS.\n\nEncrypted file downloaded.");

      // auto-download encrypted
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "encrypted_ehr.enc";
      a.click();
      a.remove();
    } catch {
      alert("❌ Encryption failed");
    } finally {
      setEncrypting(false);
    }
  };

  /* =========================
     STEP 2 — UPLOAD
  ========================= */
  const doUploadToIPFS = async () => {
    if (!encBlob) return alert("Encrypt first!");

    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", encBlob, "encrypted_ehr.enc");

      const res = await API.post("/ipfs-upload", form);
      const newCid = res.data.cid;
      setCid(newCid);

      localStorage.setItem("last_cid", newCid);
      alert(`✅ Uploaded to IPFS\nCID: ${newCid}`);
    } catch {
      alert("❌ Upload failed");
    } finally {
      setUploading(false);
    }
  };

  /* =========================
     STEP 3 — CH
  ========================= */
  const doChameleonHash = async () => {
    if (!cid) return alert("Upload to IPFS first");

    setHashing(true);
    try {
      const form = new FormData();
      form.append("cid", cid);
      form.append("public_key_hex", pub);

      const res = await API.post(`/chameleon-hash/${cid}`, form)
      const chx = res.data.ch;
      const r   = res.data.r;

      setCh(chx);
      setRHex(r);

      localStorage.setItem("ch", chx);
      localStorage.setItem("last_r", r);

      alert(`✅ CH computed\nHash: ${chx}\nr: ${r}`);
    } catch {
      alert("❌ CH compute failed");
    } finally {
      setHashing(false);
    }
  };

  /* =========================
     STEP 4 — STORE
  ========================= */
const doStoreOnChain = async () => {
  if (!wallet) return alert("Connect wallet first");
  if (!cid || !ch || !rHex) return alert("Complete previous steps");

  setStoring(true);
  try {
    let res;

    /* =========================
        REDACTION FLOW
    ========================= */
    if (isRedaction) {
      if (!encBlob) return alert("Please encrypt the revised PDF first.");

      const form = new FormData();
      form.append("file", encBlob, "encrypted_ehr.enc");
      form.append("old_cid", localStorage.getItem("last_cid") || "");
      form.append("old_r_hex", localStorage.getItem("last_r") || "");
      form.append("c_hash", localStorage.getItem("ch") || "");
      form.append("public_key_hex", pub || "");
      form.append("private_key_hex", localStorage.getItem("priv") || "");
      form.append("record_id", recordId);
      form.append("eth_address", wallet);
      form.append("consent_active", "true");

      res = await API.post("/redact", form);

      // update state
      if (res.data.new_cid) {
        setCid(res.data.new_cid);
        localStorage.setItem("last_cid", res.data.new_cid);
      }
      if (res.data.new_r) {
        setRHex(res.data.new_r);
        localStorage.setItem("last_r", res.data.new_r);
      }
      if (res.data.new_ch_hash) {
        setCh(res.data.new_ch_hash);
        localStorage.setItem("ch", res.data.new_ch_hash);
      }
      if (res.data.record_id) {
        setRecordId(res.data.record_id);
        localStorage.setItem("record_id", res.data.record_id);
      }
    }

    /* =========================
         INITIAL STORAGE FLOW
    ========================= */
    else {
      const form = new FormData();
      form.append("cid", cid);
      form.append("ch", ch);
      form.append("eth_address", wallet);

      res = await API.post("/store-record", form);

      if (res.data.record_id) {
        setRecordId(res.data.record_id);
        localStorage.setItem("record_id", res.data.record_id);
      }
    }

    /* =========================
          SEND TX
    ========================= */
    const txData = res.data.tx_data;
    if (txData) {
      const hash = await sendTx(txData);
      setTxHash(hash);
      alert(`TX Hash: ${hash}`);
    }

    setIsRedaction(false);
  } catch (e) {
    console.error("Store failed", e);
    alert("❌ Store failed");
  } finally {
    setStoring(false);
  }
};

const toggleConsent = async () => {
  if (!recordId || !wallet) return alert("No record found");

  try {
    const form = new FormData();
    form.append("record_id", recordId);
    form.append("eth_address", wallet);
    form.append("active", consentActive ? "false" : "true");

    const res = await API.post("/toggle-consent", form);
    const txData = res.data.tx_data;

    if (txData) {
      const txHash = await sendTx(txData);
      setTxHash(txHash);
      alert(`TX Hash: ${txHash}`);
    }

    setConsentActive(!consentActive);
  } catch (e) {
    console.error("Toggle failed", e);
    alert("❌ Failed toggling consent");
  }
};


  /* =========================
     VIEW
  ========================= */
  const view = async () => {
    try {
      const currentCid = localStorage.getItem("last_cid");
      if (!currentCid) return alert("No CID stored");

      const res = await API.get(`/download/${currentCid}`, { responseType: "blob" });
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

  /* =========================
     STEP MACHINE
  ========================= */
  const step = (() => {
    if (recordId) return "done";
    if (!encBlob) return "encrypt";
    if (!cid)    return "upload";
    if (!ch || !rHex) return "hash";
    if (!recordId)    return "store";
    return "done";
  })();

  const handleStep = () => {
    if (step === "encrypt") return doEncrypt();
    if (step === "upload")  return doUploadToIPFS();
    if (step === "hash")    return doChameleonHash();
    if (step === "store")   return doStoreOnChain();
  };

  const stepLabel = (() => {
    switch(step) {
      case "encrypt": return encrypting ? "Encrypting..." : "Encrypt EHR";
      case "upload":  return uploading  ? "Uploading..." : "Upload to IPFS";
      case "hash":    return hashing   ? "Computing..." : "Compute Chameleon Hash";
      case "store":   return storing   ? "Storing..."   : "Store On-Chain";
      default: return "Continue";
    }
  })();

  /* ---- Redact restarts process ---- */
  const startRedact = () => {
    setIsRedaction(true);
    setEncBlob(null);
    setCid("");
    setCh("");
    setRHex("");
    setTxHash("");
    setRecordId("");
  };

  /* =========================
     REQUEST UI
  ========================= */
  const toggleRequests = () => {
    setShowRequests(prev => {
      if (!prev) fetchRequests();
      return !prev;
    });
    setShowDropdown(false);
  };

  const toggleDropdown = () => {
    setShowDropdown(!showDropdown);
    setShowRequests(false);
  };

  const handleLogout = () => {
    window.location.href = "/";
  };

  const approveRequest = async (doctor_id, doctor_name) => {
    try {
      const form = new FormData();
      form.append("patient_id", patientName);
      form.append("doctor_id", doctor_id);
      await API.post("/approve", form);
      alert(`✅ Approved: Dr. ${doctor_name}`);
      fetchRequests();
    } catch {
      alert("❌ Failed approving");
    }
  };

  const rejectRequest = async (doctor_id, doctor_name) => {
    try {
      const form = new FormData();
      form.append("patient_id", patientName);
      form.append("doctor_id", doctor_id);
      await API.post("/reject", form);
      alert(`❌ Rejected: Dr. ${doctor_name}`);
      fetchRequests();
    } catch {
      alert("❌ Failed rejecting");
    }
  };

  /* =========================
     RENDER
  ========================= */
  return (
    <div className="patient-wrapper">
      {/* HEADER */}
      <header className="patient-header">
        <div className="left-group">
          <h2 className="app-name">EHRChain</h2>
        </div>

        <div className="right-group">
          <div className="bell" onClick={toggleRequests}>
            <FaBell size={26} />
            {requests.length > 0 && <span className="badge">{requests.length}</span>}
          </div>

          {showRequests && (
            <div className="requests-popup">
              <h3>Access Requests</h3>
              {requests.length === 0
                ? <p>No pending requests ✅</p>
                : requests.map((req, i) => {
                    const expires = new Date(req.expiresAt * 1000).toLocaleString();
                    return (
                      <div className="request-item-card" key={i}>
                        <div className="req-row">
                          <span className="label">Doctor:</span>
                          <span className="value">{req.doctor}</span>
                        </div>
                        <div className="req-row">
                          <span className="label">Record:</span>
                          <span className="value">{short(req.record_id)}</span>
                        </div>
                        <div className="req-row">
                          <span className="label">Token:</span>
                          <span className="value">{short(req.token)}</span>
                        </div>
                        <div className="req-row">
                          <span className="label">Status:</span>
                          <span className={`status ${req.status}`}>
                            {req.status}
                          </span>
                        </div>
                        <div className="req-row">
                          <span className="label">Expires:</span>
                          <span className="value">{expires}</span>
                        </div>

                        {req.status === "pending" && (
                          <div className="req-actions">
                            <FaCheck className="approve" onClick={() => approveRequest(req.doctor, req.doctor_name)} />
                            <FaTimes className="reject" onClick={() => rejectRequest(req.doctor, req.doctor_name)} />
                          </div>
                        )}
                      </div>
                    );
                  })
              }
            </div>
          )}

          <div className="user-info" onClick={toggleDropdown}>
            <FaUserCircle size={26} />
            <span>{patientName}</span>
          </div>

          {showDropdown && (
            <div className="dropdown-menu">
              <button onClick={handleLogout}>Logout</button>
            </div>
          )}
        </div>
      </header>

      {/* MAIN */}
      <div className="patient-main">
        <h1>Welcome, {patientName}!</h1>
        <p>Securely manage your health records using blockchain.</p>

        <div className="upload-card">
          <FaCloudUploadAlt className="upload-icon" />

          {/* single changing title */}
          {step === "encrypt" && <h3>1) Encrypt EHR for better safety</h3>}
          {step === "upload"  && <h3>2) Upload to IPFS (off-chain)</h3>}
          {step === "hash"    && <h3>3) Compute Chameleon Hash (Mandatory)</h3>}
          {step === "store"   && <h3>4) Store on Chain</h3>}
          {step === "done"    && <h3>✅ Stored latest EHR on blockchain</h3>}

          {step === "encrypt" && (
            <input
              type="file"
              onChange={(e) => setFile(e.target.files[0])}
            />
          )}

          {/* single action button until done */}
          {step !== "done" && (
            <button
              className="upload-btn"
              onClick={handleStep}
              disabled={
                (step === "encrypt" && (!file || !pub)) ||
                (step === "upload"  && !encBlob) ||
                (step === "hash"    && !cid) ||
                (step === "store"   && (!cid || !ch || !rHex || !wallet))
              }
            >
              {stepLabel}
            </button>
          )}

          {/* once done → show view + redact */}
          {step === "done" && (
  <>
    <button className="upload-btn" onClick={view}>
      View EHR
    </button>

    <button className="upload-btn" onClick={startRedact}>
      Edit / Redact EHR
    </button>

    {/* ✅ NEW BUTTON */}
    <button
      className="upload-btn"
      style={{ backgroundColor: consentActive ? "#f33" : "#3c3" }}
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
