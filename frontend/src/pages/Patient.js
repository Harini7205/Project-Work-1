import "../styling/patient.css";
import { useState } from "react";
import { API } from "../api/api";
import Navbar from "../components/NavBar";

export default function Patient() {
  const patientId = localStorage.getItem("wallet");
  const patientName = localStorage.getItem("name");

  const [file, setFile] = useState(null);

  const upload = async () => {
    const form = new FormData();
    form.append("file", file);
    form.append("patient_id", patientId);

    await API.post("/upload", form);
    alert("Uploaded ✅");
  };

  return (
    <>
      <Navbar />

      <div className="page patient-page">
        <h1>Patient Dashboard</h1>
        <p>Welcome, {patientName}</p>

        <input type="file" onChange={(e) => setFile(e.target.files[0])} />

        <button onClick={upload}>Upload EHR</button>
      </div>
    </>
  );
}
