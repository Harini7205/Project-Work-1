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

  // Load patient profile
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

  // Load pending records
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

  // Approve record
  const approveRecord = async (p) => {
    try {
      await sendTx(p.tx_data);
      const form = new FormData();
      form.append("pending_id", p.pending_id);
      await API.post("/patient/approve-record", form);
      alert("Record stored successfully");
      await loadPending();
      await loadPatientData();
    } catch (err) {
      console.error(err);
      alert("Transaction failed");
    }
  };

  // Toggle consent
  const toggleConsent = async () => {
    try {
      const form = new FormData();
      form.append("record_id", recordId);
      form.append("eth_address", wallet);
      form.append("active", !consent);
      const res = await API.post("/toggle-consent", form);
      await sendTx(res.data.tx_data);
      setConsent(!consent);
    } catch (err) {
      console.error(err);
      alert("Failed to update consent");
    }
  };

  // View EHR
  const viewEHR = async () => {

  if (!cid) {
    alert("No EHR uploaded yet");
    return;
  }

  try {

    const response = await fetch(
      `http://localhost:8000/ehr/download/${cid}`
    );

    if (!response.ok) {
      throw new Error("Download failed");
    }

    const blob = await response.blob();

    const url = window.URL.createObjectURL(blob);

    window.open(url, "_blank");

  } catch (err) {
    console.error(err);
    alert("Failed to download");
  }
};

  // Logout
  const logout = () => {
    localStorage.clear();
    window.location.href = "/login";
  };

  if (loading) return <div className="patient-wrapper">Loading...</div>;

  return (
    <div className="patient-wrapper">
      <div className="dashboard-header">
        <h1>Patient Dashboard</h1>
        <hr />
      </div>

      <div className="patient-main">

        {/* PROFILE CARD */}
        <div className="card profile-card">
          <h2>My Profile</h2>
          <div className="info-row">
            <div className="info-item">
              <span className="info-label">Patient ID:</span>
              <span className="info-value">{patientId || "N/A"}</span>
            </div>

            <div className="info-item">
              <span className="info-label">Consent:</span>
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
          </div>

          <div className="center-btn-row">
            <button
              className={cid ? "btn-enabled" : "btn-disabled"}
              onClick={viewEHR}
              disabled={!cid}
            >
              {cid ? "View My EHR" : "No Record Uploaded"}
            </button>
          </div>
        </div>

        {/* PENDING RECORDS */}
        {pending.length > 0 && (
          <div className="card pending-card-wrapper">
            <h2>Pending Records</h2>
            {pending.map((p) => (
              <div key={p.pending_id} className="pending-card">
                <p>New EHR uploaded by: {p.admin_wallet || "Unknown"}</p>
                <button className="btn-enabled" onClick={() => approveRecord(p)}>
                  Approve & Store On Blockchain
                </button>
              </div>
            ))}
          </div>
        )}

        {pending.length === 0 && (
          <div className="no-pending">No pending records</div>
        )}

        <div className="center-btn-row">
          <button className="btn-logout" onClick={logout}>Logout</button>
        </div>

      </div>
    </div>
  );
}
