import { useState, useEffect } from "react";
import { API } from "../api/api";
import "../styling/admin.css";

export default function Admin() {

  const wallet = localStorage.getItem("wallet");
  const pub = localStorage.getItem("pub");

  const [file, setFile] = useState(null);
  const [encBlob, setEncBlob] = useState(null);

  const [cid, setCid] = useState("");
  const [ch, setCh] = useState("");
  const [recordId, setRecordId] = useState("");

  const [patientId, setPatientId] = useState("");

  const [step, setStep] = useState(1);

  const [patients, setPatients] = useState([]);
  const [showPatients, setShowPatients] = useState(false);
  const [showLoadBtn, setShowLoadBtn] = useState(true);

  /* ===============================
     STEP 1 — ENCRYPT
  =============================== */
  const doEncrypt = async () => {
    if (!file) return alert("Choose file");
    if (!patientId) return alert("Enter Patient ID");

    const form = new FormData();
    form.append("file", file);

    const res = await API.post("/encrypt", form, {
      responseType: "blob"
    });

    setEncBlob(new Blob([res.data]));
    setStep(2);
  };

  /* ===============================
     STEP 2 — UPLOAD TO IPFS
  =============================== */
  const doUpload = async () => {
    const form = new FormData();
    form.append("file", encBlob, "encrypted.bin");

    const res = await API.post("/ipfs-upload", form);
    setCid(res.data.cid);
    setStep(3);
  };

  /* ===============================
     STEP 3 — COMPUTE HASH
  =============================== */
  const doHash = async () => {
    const form = new FormData();
    form.append("patient_id", patientId);
    form.append("cid", cid);

    const res = await API.post(`/chameleon-hash/${cid}`, form);
    setCh(res.data.ch);
    setStep(4);
  };

  /* ===============================
     STEP 4 — PREPARE (NOT STORE)
  =============================== */
  const doPrepare = async () => {
    if (!patientId) return alert("Enter Patient ID");

    const form = new FormData();
    form.append("patient_id", patientId);
    form.append("cid", cid);
    form.append("ch", ch);
    form.append("admin_wallet", wallet);

    const res = await API.post("/admin/prepare-record", form);

    setRecordId(res.data.record_id);
    setStep(5);
  };

  /* ===============================
     LOAD PATIENTS
  =============================== */
  const loadPatients = async () => {
    try {
      const res = await API.get("/patients");
      setPatients(res.data);
      setShowPatients(true);
      setShowLoadBtn(false);
      setStep(0);
    } catch {
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
          <h2>Patients</h2>
          <table>
            <thead>
              <tr>
                <th>Patient ID</th>
              </tr>
            </thead>
            <tbody>
              {patients.map((p, i) => (
                <tr key={i}>
                  <td>{p.patient_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* CENTER BOX */}
      {step !== 0 && (
        <div className="center-box">

          {step === 1 && (
            <div className="box">
              <h2>Add EHR Record</h2>
              <input
                placeholder="Enter Patient ID"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
              />
              <input
                type="file"
                onChange={(e) => setFile(e.target.files[0])}
              />
              <button onClick={doEncrypt}>Encrypt</button>
            </div>
          )}

          {step === 2 && (
            <div className="box">
              <h2>Upload to IPFS</h2>
              <button onClick={doUpload}>Upload File</button>
            </div>
          )}

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

          {step === 4 && (
            <div className="box">
              <h2>Prepare Record (Patient Approval Required)</h2>
              <div className="info-block">
                <label>CID:</label>
                <span>{cid}</span>
                <label>Chameleon Hash:</label>
                <span>{ch}</span>
              </div>
              <button onClick={doPrepare}>
                Create Pending Record
              </button>
            </div>
          )}

          {step === 5 && (
            <div className="box">
              <h2>Pending Approval</h2>
              <div className="info-block">
                <label>Patient ID:</label>
                <span>{patientId}</span>
                <label>Record ID:</label>
                <span>{recordId}</span>
                <label>CID:</label>
                <span>{cid}</span>
              </div>
              <p>
                Waiting for patient to approve and store on blockchain.
              </p>
            </div>
          )}

        </div>
      )}

    </div>
  );
}