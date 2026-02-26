import { useState, useEffect } from "react";
import { API } from "../api/api";
import "../styling/admin.css";
import { sendTx } from "./TransactionUtils";

export default function Admin() {

  const [wallet, setWallet] = useState(localStorage.getItem("wallet"));
  const [pub, setPub] = useState(localStorage.getItem("pub"));

  const [file, setFile] = useState(null);
  const [encBlob, setEncBlob] = useState(null);

  const [cid, setCid] = useState("");
  const [ch, setCh] = useState("");
  const [recordId, setRecordId] = useState("");

  const [patientId, setPatientId] = useState("");

  const [step, setStep] = useState(1);

  const [patients, setPatients] = useState([]);
  const [showPatients, setShowPatients] = useState(false);
  const [showLoadBtn, setShowLoadBtn] = useState(true); // New: control Load Patients button

  /* AUTO KEY GENERATION */
  useEffect(() => {
    const generateKeys = async () => {
      if (!pub) {
        try {
          const res = await fetch("http://127.0.0.1:8000/ehr/generate-keys", { method: "POST" });
          const data = await res.json();

          localStorage.setItem("pub", data.public_key);
          localStorage.setItem("priv", data.private_key);

          setPub(data.public_key);
        } catch {
          alert("Key generation failed");
        }
      }
    };

    generateKeys();
  }, [pub]);

  /* CONNECT WALLET */
  const connectWallet = async () => {
    if (!window.ethereum) {
      alert("Install MetaMask");
      return null;
    }

    const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
    const address = accounts[0];
    localStorage.setItem("wallet", address);
    setWallet(address);

    return address;
  };

  /* STEP 1 ENCRYPT */
  const doEncrypt = async () => {
    if (!file) return alert("Choose file");
    if (!patientId) return alert("Enter Patient ID");

    const form = new FormData();
    form.append("file", file);

    const res = await API.post("/encrypt", form, { responseType: "blob" });
    setEncBlob(new Blob([res.data]));
    setStep(2);
  };

  /* STEP 2 UPLOAD */
  const doUpload = async () => {
    const form = new FormData();
    form.append("file", encBlob, "encrypted.bin");

    const res = await API.post("/ipfs-upload", form);
    setCid(res.data.cid);
    setStep(3);
  };

  /* STEP 3 HASH */
  const doHash = async () => {
    const form = new FormData();
    form.append("public_key_hex", pub);

    const res = await API.post(`/chameleon-hash/${cid}`, form);
    setCh(res.data.ch);
    setStep(4);
  };

  /* STEP 4 STORE */
  const doStore = async () => {
    if (!patientId) return alert("Enter Patient ID");

    let currentWallet = wallet;
    if (!currentWallet) {
      currentWallet = await connectWallet();
      if (!currentWallet) return;
    }

    const form = new FormData();
    form.append("cid", cid);
    form.append("ch", ch);
    form.append("patient_id", patientId);
    form.append("eth_address", currentWallet);

    const res = await API.post("/store-record", form);
    setRecordId(res.data.record_id);

    await sendTx(res.data.tx_data);
    setStep(5);
  };

  /* LOAD PATIENTS */
  const loadPatients = async () => {
    try {
      const res = await API.get("/patients");
      setPatients(res.data);
      setShowPatients(true);
      setShowLoadBtn(false); // Hide Load button after click
      setStep(0); // Hide upload/encrypt box
    } catch (err) {
      alert("Failed to load patients");
    }
  };

  const logout = () => {
    localStorage.clear();
    window.location.href = "/";
  };

  return (
    <div>

      {/* HEADER */}
      <div className="admin-header">
        <h1>Admin Dashboard</h1>
        {showLoadBtn && (
          <button onClick={loadPatients}>Load Patients</button>
        )}
        <button className="logout-btn" onClick={logout}>Logout</button>
      </div>

      {/* PATIENT TABLE */}
      {showPatients && (
        <div className="patient-table">
          <h2>Patient Records</h2>
          <table>
            <thead>
              <tr>
                <th>Patient ID</th>
                <th>Consent Status</th>
                <th>Doctor Access</th>
              </tr>
            </thead>
            <tbody>
              {patients.map((p, i) => (
                <tr key={i}>
                  <td>{p.patient_id}</td>
                  <td>
                    <span className={p.consent ? "consent-enabled" : "consent-pending"}>
                      {p.consent ? "Enabled" : "Pending"}
                    </span>
                  </td>
                  <td>
                    <span className={p.doctor_access ? "access-yes" : "access-no"}>
                      {p.doctor_access ? "Yes" : "No"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* CENTER BOX (Steps) */}
      {step !== 0 && (
        <div className="center-box">

          {/* STEP 1 */}
          {step === 1 && (
            <div className="box">
              <h2>Add EHR Record</h2>
              <input placeholder="Enter Patient ID" value={patientId} onChange={(e) => setPatientId(e.target.value)} />
              <input type="file" onChange={(e) => setFile(e.target.files[0])} />
              <button onClick={doEncrypt}>Encrypt</button>
            </div>
          )}

          {/* STEP 2 */}
          {step === 2 && (
            <div className="box">
              <h2>Upload to IPFS</h2>
              <div className="info-block">
                <label>File selected:</label>
                <span>{file?.name || "No file chosen"}</span>
              </div>
              <button onClick={doUpload}>Upload File</button>
            </div>
          )}

          {/* STEP 3 */}
          {step === 3 && (
            <div className="box">
              <h2>Compute Chameleon Hash</h2>
              <div className="info-block">
                <label>CID:</label>
                <span>{cid}</span>
              </div>
              <button onClick={doHash}>Compute Hash</button>
            </div>
          )}

          {/* STEP 4 */}
          {step === 4 && (
            <div className="box">
              <h2>Store Record on Blockchain</h2>
              <div className="info-block">
                <label>CID:</label>
                <span>{cid}</span>
                <label>Chameleon Hash:</label>
                <span>{ch}</span>
              </div>
              <button onClick={doStore}>Store on Blockchain</button>
            </div>
          )}

          {/* STEP 5 */}
          {step === 5 && (
            <div className="box">
              <h2>Record Stored Successfully</h2>
              <div className="info-block">
                <label>Patient ID:</label>
                <span>{patientId}</span>
                <label>Record ID:</label>
                <span>{recordId}</span>
                <label>CID:</label>
                <span>{cid}</span>
                <label>Chameleon Hash:</label>
                <span>{ch}</span>
              </div>
            </div>
          )}

        </div>
      )}

    </div>
  );
}
