import { useState, useEffect } from "react";
import { API } from "../api/api";
import "../styling/patient.css";
import { sendTx } from "./TransactionUtils";

export default function Patient() {
  const name = localStorage.getItem("name");
  const wallet = localStorage.getItem("wallet");

  const [patientId, setPatientId] = useState("");
  const [consent, setConsent] = useState(false);
  const [viewEHREnabled, setViewEHREnabled] = useState(false);
  const [recordId, setRecordId] = useState("");
  const [cid, setCid] = useState("");

  /* LOAD PATIENT STATUS FROM BACKEND */
  const loadPatientStatus = async () => {
    if (!patientId) return;
    try {
      const res = await API.get(`/patient-status/${patientId}`);
      const data = res.data;
      setConsent(data.consent);
      setViewEHREnabled(data.view_ehr);
      setRecordId(data.record_id);
      setCid(data.cid);
    } catch {
      alert("Failed to load patient status");
    }
  };

  useEffect(() => {
    if (patientId) loadPatientStatus();
  }, [patientId]);

  /* GIVE CONSENT */
  const giveConsent = async () => {
    if (!patientId) return alert("Enter your Patient ID");
    try {
      const form = new FormData();
      form.append("patient_id", patientId);
      form.append("eth_address", wallet);
      form.append("active", true);

      await API.post("/give-consent", form);
      alert("Consent Given!");
      setConsent(true);
    } catch {
      alert("Failed to give consent");
    }
  };

  /* VIEW EHR */
  const viewEHR = async () => {
    if (!cid) return alert("No EHR available yet");
    try {
      const res = await API.get(`/download/${cid}`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(new Blob([res.data]));
      window.open(url);
    } catch {
      alert("Failed to view EHR");
    }
  };

  return (
    <div className="patient-wrapper">
      <h1>Welcome, {name}</h1>

      <div className="patient-card">
        <input
          placeholder="Enter your Patient ID"
          value={patientId}
          onChange={(e) => setPatientId(e.target.value)}
        />
        <button onClick={loadPatientStatus}>Load My Status</button>

        <hr />

        <h3>Consent</h3>
        <button
          disabled={consent}
          onClick={giveConsent}
          className={consent ? "btn-disabled" : "btn-enabled"}
        >
          {consent ? "Consent Given" : "Give Consent"}
        </button>

        <hr />

        <h3>View EHR</h3>
        <button
          disabled={!viewEHREnabled}
          onClick={viewEHR}
          className={viewEHREnabled ? "btn-enabled" : "btn-disabled"}
        >
          {viewEHREnabled ? "View EHR" : "Access Disabled"}
        </button>
      </div>
    </div>
  );
}
