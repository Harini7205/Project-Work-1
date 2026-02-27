import { useState, useEffect } from "react";
import { API } from "../api/api";
import "../styling/patient.css";
import { sendTx } from "./TransactionUtils";

export default function Patient() {

  const email = localStorage.getItem("email");
  const wallet = localStorage.getItem("wallet");

  const [patientId, setPatientId] = useState("");
  const [consent, setConsent] = useState(false);
  const [recordId, setRecordId] = useState("");
  const [cid, setCid] = useState("");
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState([]);

  /* ===============================
     LOAD PATIENT PROFILE
  =============================== */
  const loadPatientData = async () => {
    try {
      const res = await API.get(`/patient-profile?email=${email}`);
      const data = res.data;

      setPatientId(data.patient_id);
      setConsent(data.consent);
      setRecordId(data.record_id);
      setCid(data.cid);
    } catch (err) {
      console.error(err);
      alert("Failed to load patient data");
    }
  };

  /* ===============================
     LOAD PENDING RECORDS
  =============================== */
  const loadPending = async () => {
    try {
      const res = await API.get(`/patient/pending?email=${email}`);
      setPending(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    const init = async () => {
      await loadPatientData();
      await loadPending();
      setLoading(false);
    };

    init();
  }, []);

  /* ===============================
     APPROVE RECORD (SIGN TX)
  =============================== */
  const approveRecord = async (p) => {
    try {
      // 1️⃣ Sign blockchain transaction
      await sendTx(p.tx_data);

      // 2️⃣ Notify backend
      const form = new FormData();
      form.append("pending_id", p.pending_id);

      await API.post("/patient/approve-record", form);

      alert("Record stored successfully");

      // 3️⃣ Reload everything
      await loadPending();
      await loadPatientData();

    } catch (err) {
      console.error(err);
      alert("Transaction failed");
    }
  };

  /* ===============================
     TOGGLE CONSENT (ON-CHAIN)
  =============================== */
  const toggleConsent = async () => {
    try {
      const form = new FormData();
      form.append("record_id", recordId);
      form.append("eth_address", wallet);
      form.append("active", !consent);

      const res = await API.post("/toggle-consent", form);

      // Sign blockchain tx
      await sendTx(res.data.tx_data);

      setConsent(!consent);

    } catch (err) {
      console.error(err);
      alert("Failed to update consent");
    }
  };

  /* ===============================
     VIEW EHR
  =============================== */
  const viewEHR = async () => {
    if (!cid) return alert("No EHR uploaded yet");

    try {
      const res = await API.get(`/download/${cid}`, {
        responseType: "blob",
      });

      const url = URL.createObjectURL(new Blob([res.data]));
      window.open(url);
    } catch (err) {
      console.error(err);
      alert("Unable to fetch EHR");
    }
  };

  if (loading) {
    return <div className="patient-wrapper">Loading...</div>;
  }

  return (
    <div className="patient-wrapper">
      <h1>Patient Dashboard</h1>

      <div className="patient-card">

        {/* PATIENT ID */}
        <div className="info-row">
          <label>Patient ID</label>
          <div className="info-value">{patientId}</div>
        </div>

        <hr />

        {/* PENDING RECORDS */}
        {pending.length > 0 && (
          <>
            <h3>Pending Records</h3>
            {pending.map((p) => (
              <div key={p.pending_id} className="pending-card">
                <p>
                  New EHR uploaded by: {p.admin_wallet}
                </p>
                <button
                  className="btn-enabled"
                  onClick={() => approveRecord(p)}
                >
                  Approve & Store On Blockchain
                </button>
              </div>
            ))}
            <hr />
          </>
        )}

        {pending.length === 0 && (
          <div className="no-pending">
            No pending records
          </div>
        )}

        {/* CONSENT TOGGLE */}
        <div className="info-row">
          <label>Consent Status</label>

          <label className="switch">
            <input
              type="checkbox"
              checked={consent}
              onChange={toggleConsent}
              disabled={!recordId}
            />
            <span className="slider"></span>
          </label>

          <span className={consent ? "status-active" : "status-inactive"}>
            {consent ? "Active" : "Inactive"}
          </span>
        </div>

        <hr />

        {/* VIEW EHR */}
        <div className="info-row">
          <button
            disabled={!cid}
            onClick={viewEHR}
            className={cid ? "btn-enabled" : "btn-disabled"}
          >
            {cid ? "View My EHR" : "No Record Uploaded"}
          </button>
        </div>

      </div>
    </div>
  );
}