import { useState } from "react";
import { API } from "../api/api";
import "../styling/patient.css";
import { sendTx } from "./TransactionUtils";

export default function Patient() {

  const name = localStorage.getItem("name");
  const wallet = localStorage.getItem("wallet");

  const [recordId, setRecordId] = useState("");
  const [cid, setCid] = useState("");
  const [consent, setConsent] = useState(false);
  const [hospitals, setHospitals] = useState([]);

  // Give Consent
  const giveConsent = async () => {
    try {
      const form = new FormData();
      form.append("record_id", recordId);
      form.append("eth_address", wallet);
      form.append("active", true);

      const res = await API.post("/toggle-consent", form);

      await sendTx(res.data.tx_data);

      setConsent(true);

      alert("Consent Given");

    } catch {
      alert("Consent Failed");
    }
  };

  // View EHR
  const viewEHR = async () => {
    try {

      const res = await API.get(`/download/${cid}`, {
        responseType: "blob"
      });

      const file = new Blob([res.data]);
      const url = URL.createObjectURL(file);

      window.open(url);

    } catch {
      alert("Download Failed");
    }
  };

  // Fetch Hospitals
  const loadHospitals = async () => {
    try {
      const res = await API.get("/linked-hospitals");

      setHospitals(res.data);

    } catch {
      setHospitals([]);
    }
  };

  return (
    <div className="patient-wrapper">

      <h1>Welcome {name}</h1>

      <div className="patient-card">

        <h3>Give Consent</h3>
        <input
          placeholder="Record ID"
          onChange={(e)=>setRecordId(e.target.value)}
        />

        <button onClick={giveConsent}>
          Give Consent
        </button>

        <hr />

        <h3>View EHR</h3>

        <input
          placeholder="CID"
          onChange={(e)=>setCid(e.target.value)}
        />

        <button onClick={viewEHR}>
          View EHR
        </button>

        <hr />

        <h3>Linked Hospitals</h3>

        <button onClick={loadHospitals}>
          Load Hospitals
        </button>

        {hospitals.map((h,i)=>(
          <p key={i}>{h}</p>
        ))}

      </div>

    </div>
  );
}